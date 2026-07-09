from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trace
from app.schemas import TraceDetailResponse, TraceRead


router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRead])
def list_traces(db: Session = Depends(get_db)) -> list[Trace]:
    statement = select(Trace).order_by(Trace.timestamp.desc(), Trace.id)
    return list(db.scalars(statement).all())


@router.get("/{trace_id}", response_model=TraceDetailResponse)
def get_trace(trace_id: str, db: Session = Depends(get_db)) -> TraceDetailResponse:
    # 同一 trace 下按创建顺序返回 span，便于还原父子调用链。
    statement = (
        select(Trace)
        .where(Trace.trace_id == trace_id)
        .order_by(Trace.timestamp, Trace.id)
    )
    spans = list(db.scalars(statement).all())
    if not spans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定 trace_id",
        )
    return TraceDetailResponse(trace_id=trace_id, spans=spans)
