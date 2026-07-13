import json
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.tools import (
    bind_tool_context,
    generate_incident_report,
    get_current_alerts,
    get_recent_deployments,
    query_logs,
    query_metrics,
    query_trace,
    search_runbook,
    submit_approval,
)
from app.models import AgentSession, AgentToolCall, Approval


SERVICE_KEYWORDS = {
    "订单": "order-service",
    "order": "order-service",
    "支付": "payment-service",
    "payment": "payment-service",
    "库存": "inventory-service",
    "inventory": "inventory-service",
    "用户": "user-service",
    "user": "user-service",
    "网关": "api-gateway",
    "gateway": "api-gateway",
}
DOMAIN_KEYWORDS = ("订单", "支付", "库存", "用户", "缓存", "数据库", "接口")
TRACE_KEYWORD_WEIGHTS = {
    "slow sql": 5,
    "missing index": 5,
    "query timeout": 4,
    "connection pool exhausted": 5,
    "new version regression": 5,
    "rollback suggested": 4,
    "redis timeout": 4,
    "cache miss": 3,
    "http 500": 4,
    "returned 500": 4,
    "timeout": 1,
}


def _infer_services(query: str, alerts: list[dict[str, Any]]) -> list[str]:
    lowered_query = query.lower()
    services = {
        service
        for keyword, service in SERVICE_KEYWORDS.items()
        if keyword in lowered_query
    }
    query_domains = {keyword for keyword in DOMAIN_KEYWORDS if keyword in query}

    # 告警描述可能揭示用户未直接提及的下游故障服务。
    for alert in alerts:
        alert_text = f"{alert['title']} {alert['description']}"
        if alert["service_name"] in services or any(
            keyword in alert_text for keyword in query_domains
        ):
            services.add(alert["service_name"])

    if not services and alerts:
        services.add(alerts[0]["service_name"])
    return sorted(services)


def _select_trace_id(logs: list[dict[str, Any]]) -> str | None:
    scores: dict[str, int] = defaultdict(int)
    for item in logs:
        trace_id = item.get("trace_id")
        if not trace_id:
            continue
        message = item["message"].lower()
        scores[trace_id] += 1
        for keyword, weight in TRACE_KEYWORD_WEIGHTS.items():
            if keyword in message:
                scores[trace_id] += weight
    if not scores:
        return None
    return max(scores, key=scores.get)


def _select_runbook_query(logs: list[dict[str, Any]]) -> str:
    text = " ".join(item["message"].lower() for item in logs)
    if any(keyword in text for keyword in ("slow sql", "missing index", "query timeout")):
        return "慢 SQL"
    if "connection pool exhausted" in text:
        return "数据库连接池"
    if "redis timeout" in text or "cache miss" in text:
        return "Redis 缓存"
    if "new version regression" in text or "rollback suggested" in text:
        return "服务发布 回滚"
    return "接口超时"


def _decode_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def serialize_tool_call(tool_call: AgentToolCall) -> dict[str, Any]:
    return {
        "id": tool_call.id,
        "session_id": tool_call.session_id,
        "tool_name": tool_call.tool_name,
        "tool_input": _decode_json(tool_call.tool_input),
        "tool_output": _decode_json(tool_call.tool_output),
        "latency_ms": tool_call.latency_ms,
        "success": tool_call.success,
        "created_at": tool_call.created_at,
    }


def serialize_approval(approval: Approval | None) -> dict[str, Any] | None:
    if approval is None:
        return None
    return {
        "id": approval.id,
        "session_id": approval.session_id,
        "action_type": approval.action_type,
        "action_description": approval.action_description,
        "risk_level": approval.risk_level,
        "status": approval.status.value,
        "created_at": approval.created_at,
        "updated_at": approval.updated_at,
    }


def run_mock_diagnosis(db: Session, query: str) -> dict[str, Any]:
    session = AgentSession(user_query=query)
    db.add(session)
    db.flush()

    approval_result: dict[str, Any] | None = None
    with bind_tool_context(db, session.id):
        alerts = get_current_alerts()
        related_services = _infer_services(query, alerts)

        metrics: list[dict[str, Any]] = []
        logs: list[dict[str, Any]] = []
        deployments: list[dict[str, Any]] = []
        for service_name in related_services:
            metrics.extend(query_metrics(service_name, None))
        for service_name in related_services:
            logs.extend(query_logs(service_name, None, limit=50))

        trace_id = _select_trace_id(logs)
        traces = query_trace(trace_id)

        for service_name in related_services:
            deployments.extend(get_recent_deployments(service_name))
        runbooks = search_runbook(_select_runbook_query(logs))

        evidence = {
            "related_services": related_services,
            "selected_trace_id": trace_id,
            "alerts": alerts,
            "metrics": metrics,
            "logs": logs,
            "traces": traces,
            "deployments": deployments,
            "runbooks": runbooks,
        }
        report = generate_incident_report(evidence)

        if report["approval_action"]:
            approval_result = submit_approval(
                report["approval_action"],
                report["recommendation"],
                report["risk_level"],
            )

    session.final_answer = report["final_answer"]
    session.diagnosis_summary = report["diagnosis_summary"]
    session.root_cause = report["root_cause"]
    session.recommendation = report["recommendation"]
    session.risk_level = report["risk_level"]
    db.commit()
    db.refresh(session)

    tool_calls = db.scalars(
        select(AgentToolCall)
        .where(AgentToolCall.session_id == session.id)
        .order_by(AgentToolCall.id)
    ).all()
    approval = None
    if approval_result:
        approval = db.get(Approval, approval_result["id"])

    return {
        "session_id": session.id,
        "final_answer": session.final_answer,
        "root_cause": session.root_cause,
        "recommendation": session.recommendation,
        "risk_level": session.risk_level,
        "evidence": evidence,
        "tool_calls": [serialize_tool_call(item) for item in tool_calls],
        "approval": serialize_approval(approval),
    }
