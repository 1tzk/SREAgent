"""观测与执行连接器边界；首版实现只连接本地 SQLite 模拟环境。"""

from typing import Any, Protocol

from app.agent.tools import ToolSpec, execute_registered_tool


class ObservationConnector(Protocol):
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> tuple[ToolSpec, Any]:
        """执行只读观测工具。"""


class ExecutionConnector(Protocol):
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> tuple[ToolSpec, Any]:
        """执行受策略批准的处置工具。"""


class SQLiteObservationConnector:
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> tuple[ToolSpec, Any]:
        spec, output = execute_registered_tool(tool_name, arguments)
        if spec.side_effect:
            raise ValueError("观测连接器不能执行副作用工具")
        return spec, output


class SimulationExecutionConnector:
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> tuple[ToolSpec, Any]:
        spec, output = execute_registered_tool(tool_name, arguments)
        if not spec.side_effect:
            raise ValueError("执行连接器只能处理副作用工具")
        return spec, output


observation_connector: ObservationConnector = SQLiteObservationConnector()
simulation_execution_connector: ExecutionConnector = SimulationExecutionConnector()
