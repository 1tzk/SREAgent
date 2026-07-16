"""副作用工具的最终权限边界；模型本身没有执行权限。"""

from typing import Any

from app.agent.tools import ToolSpec
from app.config import settings


class PolicyRejectedError(ValueError):
    pass


def authorize_tool(
    spec: ToolSpec,
    arguments: dict[str, Any],
    observations: list[dict[str, Any]],
) -> None:
    if not spec.side_effect:
        return
    if settings.agent_execution_mode != "simulation":
        raise PolicyRejectedError("当前环境不允许执行自动处置")
    if not arguments.get("service_name"):
        raise PolicyRejectedError("自动处置必须指定目标服务")
    has_read_evidence = any(
        item.get("success")
        and item.get("tool_name")
        in {"query_logs", "query_metrics", "query_trace", "get_recent_deployments"}
        for item in observations
    )
    if not has_read_evidence:
        raise PolicyRejectedError("缺少只读证据，禁止自动处置")
    if any(
        item.get("success") and item.get("tool_name") == spec.name
        for item in observations
    ):
        raise PolicyRejectedError("同一运行不重复执行自动处置")
