from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Incident,
    Log,
    Metric,
    Runbook,
    Service,
)
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    services_total = db.scalar(select(func.count()).select_from(Service)) or 0
    active_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.status == AlertStatus.ACTIVE)
        )
        or 0
    )
    # TODO 当前活跃的严重告警？
    critical_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.severity == AlertSeverity.CRITICAL)
        )
        or 0
    )
    open_incidents = (
        db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.status != "resolved")
        )
        or 0
    )
    runbooks_total = db.scalar(select(func.count()).select_from(Runbook)) or 0
    metrics_total = db.scalar(select(func.count()).select_from(Metric)) or 0
    logs_total = db.scalar(select(func.count()).select_from(Log)) or 0

    status_rows = db.execute(
        select(Service.status, func.count(Service.id)).group_by(Service.status)
    ).all()
    services_by_status = {
        status.value if hasattr(status, "value") else str(status): count
        for status, count in status_rows
    }

    return DashboardSummary(
        services_total=services_total,
        services_by_status=services_by_status,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        open_incidents=open_incidents,
        runbooks_total=runbooks_total,
        metrics_total=metrics_total,
        logs_total=logs_total,
    )
