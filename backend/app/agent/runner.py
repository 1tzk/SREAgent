"""自研持久化 Agent Loop：每一步提交，服务重启后可继续执行。"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agent.llm import FinalDecision, ToolDecision, next_decision
from app.agent.connectors import (
    observation_connector,
    simulation_execution_connector,
)
from app.agent.policy import PolicyRejectedError, authorize_tool
from app.agent.tools import (
    TOOL_REGISTRY,
    bind_tool_context,
    tool_descriptions,
)
from app.config import settings
from app.database import SessionLocal
from app.models import (
    AgentRunStatus,
    AgentSession,
    AgentStep,
    AgentStepStatus,
    AgentToolCall,
    RemediationExecution,
)


logger = logging.getLogger(__name__)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _decode(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def serialize_tool_call(tool_call: AgentToolCall) -> dict[str, Any]:
    return {
        "id": tool_call.id,
        "session_id": tool_call.session_id,
        "step_id": tool_call.step_id,
        "tool_name": tool_call.tool_name,
        "tool_input": _decode(tool_call.tool_input),
        "tool_output": _decode(tool_call.tool_output),
        "latency_ms": tool_call.latency_ms,
        "success": tool_call.success,
        "created_at": tool_call.created_at,
    }


def serialize_run(session: AgentSession, include_details: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": session.id,
        "user_query": session.user_query,
        "status": session.status.value,
        "max_steps": session.max_steps,
        "steps_taken": session.steps_taken,
        "failure_reason": session.failure_reason,
        "final_answer": session.final_answer,
        "diagnosis_summary": session.diagnosis_summary,
        "root_cause": session.root_cause,
        "recommendation": session.recommendation,
        "risk_level": session.risk_level,
        "created_at": session.created_at,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
    }
    if include_details:
        result["steps"] = [
            {
                "id": step.id,
                "sequence": step.sequence,
                "decision_type": step.decision_type,
                "tool_name": step.tool_name,
                "rationale": step.rationale,
                "status": step.status.value,
                "decision_payload": _decode(step.decision_payload),
                "observation": _decode(step.observation),
                "created_at": step.created_at,
            }
            for step in sorted(session.steps, key=lambda item: item.sequence)
        ]
        result["tool_calls"] = [
            serialize_tool_call(item)
            for item in sorted(session.tool_calls, key=lambda item: item.id)
        ]
        result["remediation_executions"] = [
            {
                "id": item.id,
                "step_id": item.step_id,
                "action_type": item.action_type,
                "service_name": item.service_name,
                "status": item.status,
                "details": _decode(item.details),
                "verified": item.verified,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in sorted(session.remediation_executions, key=lambda item: item.id)
        ]
    return result


def create_agent_run(db: Session, query: str) -> AgentSession:
    session = AgentSession(
        user_query=query,
        status=AgentRunStatus.QUEUED,
        max_steps=settings.agent_max_steps,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _observations(session: AgentSession) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for step in sorted(session.steps, key=lambda item: item.sequence):
        if step.decision_type != "tool" or not step.tool_name:
            continue
        observations.append(
            {
                "tool_name": step.tool_name,
                "arguments": (_decode(step.decision_payload) or {}).get("arguments", {}),
                "output": _decode(step.observation),
                "success": step.status == AgentStepStatus.SUCCEEDED,
            }
        )
    return observations


def _finish(session: AgentSession, decision: FinalDecision) -> None:
    session.final_answer = decision.final_answer
    session.diagnosis_summary = decision.summary
    session.root_cause = decision.root_cause
    session.recommendation = decision.recommendation
    session.risk_level = decision.risk_level
    session.status = AgentRunStatus.COMPLETED
    session.completed_at = datetime.utcnow()
    session.failure_reason = None


def run_agent_session(session_id: int) -> None:
    """每个 Tool Step 单独提交，避免进程中断时丢失已完成的审计。"""
    db = SessionLocal()
    try:
        session = db.get(AgentSession, session_id)
        if session is None or session.status not in {
            AgentRunStatus.QUEUED,
            AgentRunStatus.RUNNING,
        }:
            return
        session.status = AgentRunStatus.RUNNING
        session.started_at = session.started_at or datetime.utcnow()
        db.commit()

        observations = _observations(session)
        for sequence in range(session.steps_taken + 1, session.max_steps + 1):
            decision = next_decision(session.user_query, observations, tool_descriptions())
            tool_name = decision.tool_name if isinstance(decision, ToolDecision) else None
            step = AgentStep(
                session_id=session.id,
                sequence=sequence,
                decision_type=decision.type,
                tool_name=tool_name,
                rationale=decision.rationale,
                status=AgentStepStatus.PLANNED,
                decision_payload=_json(decision.model_dump()),
            )
            db.add(step)
            db.flush()

            if isinstance(decision, FinalDecision):
                step.status = AgentStepStatus.SUCCEEDED
                step.observation = _json({"result": "finalized"})
                session.steps_taken = sequence
                _finish(session, decision)
                db.commit()
                return

            try:
                # 保持策略校验与真实调用之间没有模型直连路径。
                registry_spec = TOOL_REGISTRY.get(decision.tool_name)
                if registry_spec is None:
                    raise ValueError(f"工具未注册：{decision.tool_name}")
                authorize_tool(registry_spec, decision.arguments, observations)
                with bind_tool_context(db, session.id, step.id):
                    connector = (
                        simulation_execution_connector
                        if registry_spec.side_effect
                        else observation_connector
                    )
                    actual_spec, output = connector.execute(
                        decision.tool_name,
                        decision.arguments,
                    )
                step.status = AgentStepStatus.SUCCEEDED
                step.observation = _json(output)
                if actual_spec.side_effect:
                    db.add(
                        RemediationExecution(
                            session_id=session.id,
                            step_id=step.id,
                            action_type=actual_spec.name,
                            service_name=str(decision.arguments["service_name"]),
                            status="succeeded",
                            details=_json(output),
                            verified=False,
                        )
                    )
                elif observations and any(
                    item.get("tool_name", "").startswith("simulate_")
                    and item.get("success")
                    for item in observations
                ):
                    for execution in db.scalars(
                        select(RemediationExecution).where(
                            RemediationExecution.session_id == session.id
                        )
                    ).all():
                        if not execution.verified and execution.status == "succeeded":
                            execution.verified = True
                observations.append(
                    {
                        "tool_name": decision.tool_name,
                        "arguments": decision.arguments,
                        "output": output,
                        "success": True,
                    }
                )
            except PolicyRejectedError as exc:
                step.status = AgentStepStatus.REJECTED
                step.observation = _json({"error": str(exc)})
                observations.append(
                    {
                        "tool_name": decision.tool_name,
                        "arguments": decision.arguments,
                        "output": {"error": str(exc)},
                        "success": False,
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Agent tool failed; session_id=%s tool=%s error=%s",
                    session.id,
                    decision.tool_name,
                    type(exc).__name__,
                )
                step.status = AgentStepStatus.FAILED
                step.observation = _json({"error": str(exc)})
                observations.append(
                    {
                        "tool_name": decision.tool_name,
                        "arguments": decision.arguments,
                        "output": {"error": str(exc)},
                        "success": False,
                    }
                )
            session.steps_taken = sequence
            db.commit()

        session.status = AgentRunStatus.STOPPED
        session.failure_reason = f"超过最大轮次限制：{session.max_steps}"
        session.completed_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()
        session = db.get(AgentSession, session_id)
        if session is not None:
            session.status = AgentRunStatus.FAILED
            session.failure_reason = "Agent 执行器发生未处理错误"
            session.completed_at = datetime.utcnow()
            db.commit()
        logger.exception("Agent run failed; session_id=%s", session_id)
    finally:
        db.close()


def recover_interrupted_runs() -> None:
    db = SessionLocal()
    try:
        # 单实例启动时将未完成状态重新入队，保证已提交的步骤可从数据库恢复。
        db.execute(
            update(AgentSession)
            .where(AgentSession.status == AgentRunStatus.RUNNING)
            .values(status=AgentRunStatus.QUEUED)
        )
        db.commit()
    finally:
        db.close()


def run_next_queued_session() -> bool:
    db = SessionLocal()
    try:
        session_id = db.scalar(
            select(AgentSession.id)
            .where(AgentSession.status == AgentRunStatus.QUEUED)
            .order_by(AgentSession.created_at, AgentSession.id)
            .limit(1)
        )
    finally:
        db.close()
    if session_id is None:
        return False
    run_agent_session(session_id)
    return True


class AgentRunWorker:
    """SQLite POC 使用单 worker；未来真实部署可替换为独立队列消费者。"""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    async def start(self) -> None:
        recover_interrupted_runs()
        self._task = asyncio.create_task(self._work(), name="agent-run-worker")

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            await self._task

    async def _work(self) -> None:
        while not self._stopping:
            found = await asyncio.to_thread(run_next_queued_session)
            if not found:
                await asyncio.sleep(0.25)
