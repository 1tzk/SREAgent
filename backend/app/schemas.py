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
