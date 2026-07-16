from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str


class ServiceRead(BaseModel):
    id: int
    name: str
    display_name: str
    status: str
    owner: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeedResetResponse(BaseModel):
    status: str
    services: int
    logs: int
    metrics: int
    runbooks: int


class DashboardSummary(BaseModel):
    services_total: int
    services_by_status: dict[str, int]
    active_alerts: int
    critical_alerts: int
    open_incidents: int
    runbooks_total: int
    metrics_total: int
    logs_total: int


class AlertRead(BaseModel):
    id: int
    service_name: str
    severity: str
    title: str
    description: str
    status: str
    started_at: datetime
    resolved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogRead(BaseModel):
    id: int
    service_name: str
    level: str
    message: str
    trace_id: str | None
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricRead(BaseModel):
    id: int
    service_name: str
    metric_name: str
    metric_value: float
    unit: str
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TraceRead(BaseModel):
    id: int
    trace_id: str
    span_id: str
    parent_span_id: str | None
    service_name: str
    operation_name: str
    duration_ms: float
    status: str
    error_message: str | None
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentRead(BaseModel):
    id: int
    service_name: str
    version: str
    operator: str
    description: str
    status: str
    deployed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentRead(BaseModel):
    id: int
    title: str
    severity: str
    status: str
    affected_services: str
    root_cause: str | None
    summary: str | None
    recommendation: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentTimelineItem(BaseModel):
    occurred_at: datetime
    event_type: str
    title: str
    description: str


class EvidenceSource(BaseModel):
    evidence_type: str
    title: str
    description: str
    service_name: str | None


class IncidentReportResponse(BaseModel):
    incident_id: int
    title: str
    severity: str
    affected_services: list[str]
    timeline: list[IncidentTimelineItem]
    root_cause: str
    evidence_sources: list[EvidenceSource]
    recommendation: str
    prevention: str
    requires_approval: bool


class TraceDetailResponse(BaseModel):
    trace_id: str
    spans: list[TraceRead]


class ScenarioResponse(BaseModel):
    scenario: str
    trace_id: str
    alert: AlertRead
    incident: IncidentRead
    deployment: DeploymentRead | None = None
    records_created: dict[str, int]


class DiagnoseRequest(BaseModel):
    query: str


class AgentToolCallRead(BaseModel):
    id: int
    session_id: int
    step_id: int | None
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Any
    latency_ms: int
    success: bool
    created_at: datetime


class ApprovalRead(BaseModel):
    id: int
    session_id: int
    action_type: str
    action_description: str
    risk_level: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentSessionRead(BaseModel):
    id: int
    user_query: str
    status: str
    max_steps: int
    steps_taken: int
    failure_reason: str | None
    final_answer: str | None
    diagnosis_summary: str | None
    root_cause: str | None
    recommendation: str | None
    risk_level: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AgentStepRead(BaseModel):
    id: int
    sequence: int
    decision_type: str
    tool_name: str | None
    rationale: str
    status: str
    decision_payload: dict[str, Any]
    observation: Any
    created_at: datetime


class RemediationExecutionRead(BaseModel):
    id: int
    step_id: int | None
    action_type: str
    service_name: str
    status: str
    details: Any
    verified: bool
    created_at: datetime
    updated_at: datetime


class AgentSessionDetail(AgentSessionRead):
    steps: list[AgentStepRead]
    tool_calls: list[AgentToolCallRead]
    remediation_executions: list[RemediationExecutionRead]


class DiagnoseResponse(BaseModel):
    session_id: int
    final_answer: str
    root_cause: str
    recommendation: str
    risk_level: str
    evidence: dict[str, Any]
    tool_calls: list[AgentToolCallRead]
    approval: ApprovalRead | None
