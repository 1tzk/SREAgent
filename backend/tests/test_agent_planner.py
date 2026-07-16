import pytest
from pydantic import ValidationError

from app.agent.llm import FinalDecision, ToolDecision, mock_next_decision
from app.agent.policy import PolicyRejectedError, authorize_tool
from app.agent.tools import TOOL_REGISTRY, execute_registered_tool, tool_descriptions


def _mock_output(tool_name: str):
    if tool_name == "get_current_alerts":
        return [{"service_name": "inventory-service"}]
    if tool_name == "query_logs":
        return [{"trace_id": "slow-sql-001", "message": "slow SQL missing index"}]
    if tool_name == "query_metrics":
        return [{"service_name": "inventory-service", "metric_name": "p95_latency"}]
    if tool_name == "query_trace":
        return [{"trace_id": "slow-sql-001", "service_name": "inventory-service"}]
    if tool_name == "get_recent_deployments":
        return [{"service_name": "inventory-service", "version": "v1.8.3"}]
    if tool_name == "search_runbook":
        return [{"title": "慢 SQL 排查手册"}]
    return {"status": "simulated"}


def test_mock_planner_replays_slow_sql_with_verified_remediation() -> None:
    observations = []
    actions = []
    decision = None
    for _ in range(12):
        decision = mock_next_decision(
            "库存服务最近延迟升高，帮我定位根因。",
            observations,
        )
        if isinstance(decision, FinalDecision):
            break
        assert isinstance(decision, ToolDecision)
        actions.append(decision.tool_name)
        observations.append(
            {
                "tool_name": decision.tool_name,
                "arguments": decision.arguments,
                "output": _mock_output(decision.tool_name),
                "success": True,
            }
        )

    assert isinstance(decision, FinalDecision)
    assert "simulate_rollback_deployment" in actions
    assert actions.index("simulate_rollback_deployment") < actions.index(
        "query_metrics", actions.index("simulate_rollback_deployment") + 1
    )


def test_policy_requires_observation_before_simulated_side_effect() -> None:
    spec = TOOL_REGISTRY["simulate_restart_service"]
    with pytest.raises(PolicyRejectedError):
        authorize_tool(spec, {"service_name": "user-service"}, [])

    authorize_tool(
        spec,
        {"service_name": "user-service"},
        [{"tool_name": "query_logs", "success": True, "output": []}],
    )


def test_tool_registry_rejects_invalid_input_before_execution() -> None:
    with pytest.raises(ValidationError):
        execute_registered_tool(
            "simulate_scale_service",
            {"service_name": "order-service", "replicas": 99},
        )

    assert any(item["name"] == "query_logs" for item in tool_descriptions())
