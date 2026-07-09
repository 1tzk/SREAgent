from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Metric
from app.schemas import MetricRead


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricRead])
def list_metrics(
    service_name: str | None = None,
    metric_name: str | None = None,
    db: Session = Depends(get_db),
) -> list[Metric]:
    statement = select(Metric)
    if service_name:
        statement = statement.where(Metric.service_name == service_name)
    if metric_name:
        statement = statement.where(Metric.metric_name == metric_name)
    statement = statement.order_by(Metric.timestamp.desc(), Metric.id.desc())
    return list(db.scalars(statement).all())
