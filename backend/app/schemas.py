from datetime import datetime

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
