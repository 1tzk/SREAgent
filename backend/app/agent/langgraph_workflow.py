"""由 LangGraph 编排的确定性诊断工作流。

图只负责按固定顺序执行已审计工具；LLM 不参与工具选择或审批决策。
"""

from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_for_diagnosis
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
from app.agent.workflow import (
    _infer_services,
    _select_runbook_query,
    _select_trace_id,
    serialize_approval,
    serialize_tool_call,
)
from app.models import AgentSession, AgentToolCall, Approval


class DiagnosisState(TypedDict, total=False):
    """节点间传递的诊断状态；每个节点仅写入自己产出的字段。"""

    db: Session
    query: str
    session_id: int
    alerts: list[dict[str, Any]]
    related_services: list[str]
    metrics: list[dict[str, Any]]
    logs: list[dict[str, Any]]
    selected_trace_id: str | None
    traces: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    runbooks: list[dict[str, Any]]
    evidence: dict[str, Any]
    report: dict[str, Any]
    approval_result: dict[str, Any] | None
    result: dict[str, Any]


def collect_alerts(state: DiagnosisState) -> dict[str, Any]:
    """输入 query/session_id；输出 alerts。"""
    return {"alerts": get_current_alerts()}


def identify_services(state: DiagnosisState) -> dict[str, Any]:
    """输入 query 和 alerts；输出 related_services。"""
    return {
        "related_services": _infer_services(
            state["query"],
            state.get("alerts", []),
        )
    }


def collect_metrics(state: DiagnosisState) -> dict[str, Any]:
    """输入 related_services；输出所有相关服务的 metrics。"""
    metrics: list[dict[str, Any]] = []
    for service_name in state.get("related_services", []):
        metrics.extend(query_metrics(service_name, None))
    return {"metrics": metrics}


def collect_logs(state: DiagnosisState) -> dict[str, Any]:
    """输入 related_services；输出限定数量的 logs。"""
    logs: list[dict[str, Any]] = []
    for service_name in state.get("related_services", []):
        logs.extend(query_logs(service_name, None, limit=50))
    return {"logs": logs}


def collect_traces(state: DiagnosisState) -> dict[str, Any]:
    """输入 logs；输出选中的 trace ID 及对应 traces。"""
    trace_id = _select_trace_id(state.get("logs", []))
    return {
        "selected_trace_id": trace_id,
        "traces": query_trace(trace_id) if trace_id else [],
    }


def collect_deployments(state: DiagnosisState) -> dict[str, Any]:
    """输入 related_services；输出 deployments。"""
    deployments: list[dict[str, Any]] = []
    for service_name in state.get("related_services", []):
        deployments.extend(get_recent_deployments(service_name))
    return {"deployments": deployments}


def retrieve_runbooks(state: DiagnosisState) -> dict[str, Any]:
    """输入 logs；输出与诊断线索匹配的 runbooks。"""
    return {"runbooks": search_runbook(_select_runbook_query(state.get("logs", [])))}


def analyze_root_cause(state: DiagnosisState) -> dict[str, Any]:
    """输入所有已收集证据；输出结构化 evidence 与确定性 report。"""
    evidence = {
        "related_services": state.get("related_services", []),
        "selected_trace_id": state.get("selected_trace_id"),
        "alerts": state.get("alerts", []),
        "metrics": state.get("metrics", []),
        "logs": state.get("logs", []),
        "traces": state.get("traces", []),
        "deployments": state.get("deployments", []),
        "runbooks": state.get("runbooks", []),
        "typed_evidence": [
            {"type": "alert", "records": state.get("alerts", [])},
            {"type": "metric", "records": state.get("metrics", [])},
            {"type": "log", "records": state.get("logs", [])},
            {"type": "trace", "records": state.get("traces", [])},
            {"type": "deployment", "records": state.get("deployments", [])},
            {"type": "runbook", "records": state.get("runbooks", [])},
        ],
    }
    return {
        "evidence": evidence,
        "report": generate_incident_report(evidence),
    }


def generate_recommendation(state: DiagnosisState) -> dict[str, Any]:
    """输入确定性 report 与 evidence；输出仅润色文本后的 report。"""
    report = dict(state["report"])
    llm_response = call_llm_for_diagnosis(
        {
            "query": state["query"],
            "evidence": state["evidence"],
            "mock_report": report,
        }
    )
    # 根因、风险和审批动作仍由确定性规则报告控制。
    report["final_answer"] = llm_response["final_answer"]
    report["diagnosis_summary"] = llm_response["summary"]
    report["recommendation"] = llm_response["recommendation"]
    return {"report": report}


def create_approval_if_needed(state: DiagnosisState) -> dict[str, Any]:
    """输入 report；需要人工操作时输出 approval_result，否则输出 None。"""
    report = state["report"]
    if not report["approval_action"]:
        return {"approval_result": None}
    return {
        "approval_result": submit_approval(
            report["approval_action"],
            report["recommendation"],
            report["risk_level"],
        )
    }


def save_session(state: DiagnosisState) -> dict[str, Any]:
    """输入 report/approval_result；提交 session 并输出保持原 API 结构的 result。"""
    db = state["db"]
    session = db.get(AgentSession, state["session_id"])
    if session is None:
        raise RuntimeError("Agent session was not created")

    report = state["report"]
    session.final_answer = report["final_answer"]
    session.diagnosis_summary = report["diagnosis_summary"]
    session.root_cause = report["root_cause"]
    session.recommendation = report["recommendation"]
    session.risk_level = report["risk_level"]
    # 图尚未结束前只 flush，外层确认图成功后再统一提交整个诊断事务。
    db.flush()

    tool_calls = db.scalars(
        select(AgentToolCall)
        .where(AgentToolCall.session_id == session.id)
        .order_by(AgentToolCall.id)
    ).all()
    approval_result = state.get("approval_result")
    approval = db.get(Approval, approval_result["id"]) if approval_result else None
    return {
        "result": {
            "session_id": session.id,
            "final_answer": session.final_answer,
            "root_cause": session.root_cause,
            "recommendation": session.recommendation,
            "risk_level": session.risk_level,
            "evidence": state["evidence"],
            "tool_calls": [serialize_tool_call(item) for item in tool_calls],
            "approval": serialize_approval(approval),
        }
    }


@lru_cache(maxsize=1)
def build_langgraph_workflow():
    """构建固定有向图，节点顺序不由 LLM 决定。"""
    workflow = StateGraph(DiagnosisState)
    workflow.add_node("collect_alerts", collect_alerts)
    workflow.add_node("identify_services", identify_services)
    workflow.add_node("collect_metrics", collect_metrics)
    workflow.add_node("collect_logs", collect_logs)
    workflow.add_node("collect_traces", collect_traces)
    workflow.add_node("collect_deployments", collect_deployments)
    workflow.add_node("retrieve_runbooks", retrieve_runbooks)
    workflow.add_node("analyze_root_cause", analyze_root_cause)
    workflow.add_node("generate_recommendation", generate_recommendation)
    workflow.add_node("create_approval_if_needed", create_approval_if_needed)
    workflow.add_node("save_session", save_session)

    workflow.add_edge(START, "collect_alerts")
    workflow.add_edge("collect_alerts", "identify_services")
    workflow.add_edge("identify_services", "collect_metrics")
    workflow.add_edge("collect_metrics", "collect_logs")
    workflow.add_edge("collect_logs", "collect_traces")
    workflow.add_edge("collect_traces", "collect_deployments")
    workflow.add_edge("collect_deployments", "retrieve_runbooks")
    workflow.add_edge("retrieve_runbooks", "analyze_root_cause")
    workflow.add_edge("analyze_root_cause", "generate_recommendation")
    workflow.add_edge("generate_recommendation", "create_approval_if_needed")
    workflow.add_edge("create_approval_if_needed", "save_session")
    workflow.add_edge("save_session", END)
    return workflow.compile()


def run_langgraph_diagnosis(db: Session, query: str) -> dict[str, Any]:
    """创建会话后执行图；节点工具调用会沿用现有审计上下文。"""
    session = AgentSession(user_query=query)
    db.add(session)
    db.flush()

    try:
        with bind_tool_context(db, session.id):
            final_state = build_langgraph_workflow().invoke(
                {
                    "db": db,
                    "query": query,
                    "session_id": session.id,
                }
            )
        result = final_state.get("result")
        if result is None:
            raise RuntimeError("LangGraph workflow completed without a result")
        db.commit()
        return result
    except Exception:
        # 失败时撤销本次会话和工具审计，供外层安全回退到原 Mock workflow。
        db.rollback()
        raise
