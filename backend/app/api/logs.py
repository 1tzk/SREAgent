from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Log
from app.schemas import LogRead


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[LogRead])
def list_logs(
    service_name: str | None = None,
    keyword: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> list[Log]:
    statement = select(Log)
    if service_name:
        statement = statement.where(Log.service_name == service_name)
    if keyword:
        statement = statement.where(Log.message.ilike(f"%{keyword}%"))
    statement = statement.order_by(Log.timestamp.desc(), Log.id.desc())
    return list(db.scalars(statement).all())
