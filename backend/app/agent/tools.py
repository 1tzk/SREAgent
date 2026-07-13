import inspect
import json
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from time import perf_counter
from typing import Any, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentToolCall,
    Alert,
    AlertStatus,
    Approval,
    ApprovalStatus,
    Deployment,
    Log,
    Metric,
    Runbook,
    Trace,
)


@dataclass(frozen=True)
class AgentToolContext:
    db: Session
    session_id: int


_tool_context: ContextVar[AgentToolContext | None] = ContextVar(
    "agent_tool_context",
    default=None,
)
ToolFunction = TypeVar("ToolFunction", bound=Callable[..., Any])


@contextmanager
def bind_tool_context(db: Session, session_id: int) -> Iterator[None]:
    """为当前诊断请求绑定数据库会话和审计所需的 session_id。"""
    token = _tool_context.set(AgentToolContext(db=db, session_id=session_id))
    try:
        yield
    finally:
        _tool_context.reset(token)


def _current_context() -> AgentToolContext:
    context = _tool_context.get()
    if context is None:
        raise RuntimeError("Agent 工具必须在 bind_tool_context 中调用")
    return context


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _to_dict(model: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Enum):
            value = value.value
        result[column.name] = value
    return result


def _record_tool_call(
    context: AgentToolContext,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: Any,
    latency_ms: int,
    success: bool,
) -> None:
    context.db.add(
        AgentToolCall(
            session_id=context.session_id,
            tool_name=tool_name,
            tool_input=json.dumps(tool_input, ensure_ascii=False, default=_json_default),
            tool_output=json.dumps(tool_output, ensure_ascii=False, default=_json_default),
            latency_ms=latency_ms,
            success=success,
        )
    )
    context.db.flush()


def audited_tool(function: ToolFunction) -> ToolFunction:
    """统一记录工具输入、输出、耗时和执行状态。"""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        context = _current_context()
        bound = inspect.signature(function).bind(*args, **kwargs)
        bound.apply_defaults()
        tool_input = dict(bound.arguments)
        started_at = perf_counter()
        try:
            output = function(*args, **kwargs)
        except Exception as exc:
            latency_ms = max(0, round((perf_counter() - started_at) * 1000))
            _record_tool_call(
                context,
                function.__name__,
                tool_input,
                {"error": str(exc)},
                latency_ms,
                False,
            )
            raise

        latency_ms = max(0, round((perf_counter() - started_at) * 1000))
        _record_tool_call(
            context,
            function.__name__,
            tool_input,
            output,
            latency_ms,
            True,
        )
        return output

    return cast(ToolFunction, wrapper)


@audited_tool
def get_current_alerts() -> list[dict[str, Any]]:
    context = _current_context()
    statement = (
        select(Alert)
        .where(Alert.status == AlertStatus.ACTIVE)
        .order_by(Alert.started_at.desc(), Alert.id.desc())
    )
    return [_to_dict(item) for item in context.db.scalars(statement).all()]


@audited_tool
def query_logs(
    service_name: str | None,
    keyword: str | None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    context = _current_context()
    safe_limit = min(max(limit, 1), 100)
    statement = select(Log)
    if service_name:
        statement = statement.where(Log.service_name == service_name)
    if keyword:
        statement = statement.where(Log.message.ilike(f"%{keyword}%"))
    statement = statement.order_by(Log.timestamp.desc(), Log.id.desc()).limit(safe_limit)
    return [_to_dict(item) for item in context.db.scalars(statement).all()]


@audited_tool
def query_metrics(
    service_name: str | None,
    metric_name: str | None,
) -> list[dict[str, Any]]:
    context = _current_context()
    statement = select(Metric)
    if service_name:
        statement = statement.where(Metric.service_name == service_name)
    if metric_name:
        statement = statement.where(Metric.metric_name == metric_name)
    statement = statement.order_by(Metric.timestamp.desc(), Metric.id.desc()).limit(100)
    return [_to_dict(item) for item in context.db.scalars(statement).all()]


@audited_tool
def query_trace(trace_id: str | None) -> list[dict[str, Any]]:
    context = _current_context()
    statement = select(Trace)
    if trace_id:
        statement = statement.where(Trace.trace_id == trace_id)
    statement = statement.order_by(Trace.timestamp.desc(), Trace.id).limit(100)
    return [_to_dict(item) for item in context.db.scalars(statement).all()]


@audited_tool
def get_recent_deployments(
    service_name: str | None,
) -> list[dict[str, Any]]:
    context = _current_context()
    statement = select(Deployment)
    if service_name:
        statement = statement.where(Deployment.service_name == service_name)
    statement = statement.order_by(
        Deployment.deployed_at.desc(),
        Deployment.id.desc(),
    ).limit(10)
    return [_to_dict(item) for item in context.db.scalars(statement).all()]


def rank_runbooks(db: Session, query: str) -> list[dict[str, Any]]:
    """按标题、分类、标签和正文的命中位置计算稳定的关键词评分。"""
    tokens = re.findall(r"[A-Za-z0-9_-]+|[\u4e00-\u9fff]+", query)
    if not tokens:
        return []

    ranked: list[dict[str, Any]] = []
    for runbook in db.scalars(select(Runbook).order_by(Runbook.updated_at.desc())).all():
        fields = (
            (runbook.title.lower(), 5),
            (runbook.category.lower(), 3),
            (runbook.tags.lower(), 2),
            (runbook.content.lower(), 1),
        )
        score = 0
        matched_keywords: list[str] = []
        for token in tokens:
            normalized_token = token.lower()
            token_score = sum(
                weight for field_value, weight in fields if normalized_token in field_value
            )
            if token_score:
                score += token_score
                matched_keywords.append(token)
        if score:
            ranked.append(
                {
                    "title": runbook.title,
                    "score": score,
                    "content": runbook.content,
                    "matched_keywords": matched_keywords,
                }
            )
    return sorted(ranked, key=lambda item: (-item["score"], item["title"]))[:10]


@audited_tool
def search_runbook(query: str) -> list[dict[str, Any]]:
    context = _current_context()
    return rank_runbooks(context.db, query)


def _has_high_metric(
    metrics: list[dict[str, Any]],
    service_name: str,
    metric_name: str,
    threshold: float,
) -> bool:
    return any(
        item["service_name"] == service_name
        and item["metric_name"] == metric_name
        and float(item["metric_value"]) >= threshold
        for item in metrics
    )


def _contains_log(
    logs: list[dict[str, Any]],
    service_name: str,
    keywords: tuple[str, ...],
) -> bool:
    return any(
        item["service_name"] == service_name
        and any(keyword in item["message"].lower() for keyword in keywords)
        for item in logs
    )


@audited_tool
def generate_incident_report(context: dict) -> dict[str, Any]:
    metrics = context.get("metrics", [])
    logs = context.get("logs", [])
    traces = context.get("traces", [])
    deployments = context.get("deployments", [])
    runbooks = context.get("runbooks", [])
    runbook_titles = "、".join(item["title"] for item in runbooks[:3])
    runbook_reference = f"\nRunbook 参考：{runbook_titles}" if runbook_titles else ""

    slow_order = _has_high_metric(metrics, "order-service", "p95_latency", 500)
    slow_inventory = _has_high_metric(
        metrics,
        "inventory-service",
        "p95_latency",
        500,
    )
    slow_sql_logs = _contains_log(
        logs,
        "inventory-service",
        ("slow sql", "missing index", "query timeout"),
    )
    inventory_deployment = any(
        item["service_name"] == "inventory-service" for item in deployments
    )
    slowest_span = max(traces, key=lambda item: item["duration_ms"], default=None)

    # 五项证据同时命中时，输出稳定且可测试的慢 SQL 诊断结论。
    if (
        slow_order
        and slow_inventory
        and slow_sql_logs
        and inventory_deployment
        and slowest_span
        and slowest_span["service_name"] == "inventory-service"
    ):
        root_cause = (
            "inventory-service 最近版本可能引入低效 SQL，导致库存查询变慢，"
            "进而拖慢订单接口。"
        )
        recommendation = (
            "优先回滚 inventory-service 最近版本，并检查 SQL 执行计划、"
            "索引和数据库连接池。"
        )
        return {
            "diagnosis_summary": "订单链路延迟主要集中在 inventory-service 的数据库查询。",
            "final_answer": (
                f"诊断结论：{root_cause}\n"
                f"关键证据：order-service 与 inventory-service 的 P95 延迟均明显升高；"
                f"inventory-service 是链路最慢 span（{slowest_span['duration_ms']}ms）；"
                "日志出现 slow SQL、missing index 或 query timeout；"
                "且该服务近期存在发布记录。\n"
                f"处理建议：{recommendation}{runbook_reference}"
            ),
            "root_cause": root_cause,
            "recommendation": recommendation,
            "risk_level": "high",
            "approval_action": "rollback_deployment",
        }

    log_text = " ".join(item["message"].lower() for item in logs)
    metric_names = {
        (item["service_name"], item["metric_name"]): float(item["metric_value"])
        for item in metrics
    }

    if "connection pool exhausted" in log_text:
        root_cause = "数据库连接池耗尽导致多个服务等待连接，进而引发链路延迟。"
        recommendation = "检查长事务和连接泄漏，并审批后扩容数据库连接池。"
        risk_level = "high"
        approval_action = "change_database_config"
    elif "new version regression" in log_text or "rollback suggested" in log_text:
        root_cause = "最近发布的新版本出现回归，服务错误率在发布后明显升高。"
        recommendation = "优先回滚最近版本，并补充兼容性测试后再重新发布。"
        risk_level = "high"
        approval_action = "rollback_deployment"
    elif "redis timeout" in log_text or "cache miss" in log_text:
        root_cause = "Redis 访问异常导致缓存命中率下降，请求大量回源并拉高延迟。"
        recommendation = "检查 Redis 节点和连接状态，审批后重启异常缓存客户端实例。"
        risk_level = "medium"
        approval_action = "restart_service"
    elif "http 500" in log_text or "returned 500" in log_text:
        root_cause = "服务内部异常导致 500 错误率升高，失败点可由错误 span 定位。"
        recommendation = "检查错误堆栈和下游响应，隔离异常实例并修复后发布。"
        risk_level = "high"
        approval_action = None
    elif "timeout" in log_text:
        root_cause = "服务处理或下游调用超时，链路中的高耗时 span 是主要瓶颈。"
        recommendation = "检查线程池与下游依赖，审批后按容量评估结果扩容服务。"
        risk_level = "medium"
        approval_action = "scale_service"
    elif any(name == "error_rate" and value >= 5 for (_, name), value in metric_names.items()):
        root_cause = "监控显示服务错误率异常升高，但当前证据不足以确定具体代码路径。"
        recommendation = "结合错误日志和更完整的链路数据继续定位异常来源。"
        risk_level = "medium"
        approval_action = None
    else:
        root_cause = "当前工具证据未发现明确的单一故障根因。"
        recommendation = "持续观察告警、延迟和错误率，并补充更具体的服务或时间范围。"
        risk_level = "low"
        approval_action = None

    return {
        "diagnosis_summary": root_cause,
        "final_answer": (
            f"诊断结论：{root_cause}\n"
            f"已检查 {len(metrics)} 个指标点、{len(logs)} 条日志和 "
            f"{len(traces)} 个链路 span。\n"
            f"处理建议：{recommendation}{runbook_reference}"
        ),
        "root_cause": root_cause,
        "recommendation": recommendation,
        "risk_level": risk_level,
        "approval_action": approval_action,
    }


@audited_tool
def submit_approval(
    action_type: str,
    action_description: str,
    risk_level: str,
) -> dict[str, Any]:
    context = _current_context()
    approval = Approval(
        session_id=context.session_id,
        action_type=action_type,
        action_description=action_description,
        risk_level=risk_level,
        status=ApprovalStatus.PENDING,
    )
    context.db.add(approval)
    context.db.flush()
    return _to_dict(approval)
