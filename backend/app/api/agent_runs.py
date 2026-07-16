from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.runner import create_agent_run, serialize_run
from app.database import get_db
from app.models import AgentSession
from app.schemas import AgentSessionDetail, AgentSessionRead, DiagnoseRequest


router = APIRouter(prefix="/agent", tags=["agent"])


def _get_run_or_404(db: Session, session_id: int) -> AgentSession:
    statement = (
        select(AgentSession)
        .options(
            selectinload(AgentSession.steps),
            selectinload(AgentSession.tool_calls),
            selectinload(AgentSession.remediation_executions),
        )
        .where(AgentSession.id == session_id)
    )
    session = db.scalar(statement)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到指定 Agent Run")
    return session


@router.post(
    "/runs",
    response_model=AgentSessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_agent_run(
    request: DiagnoseRequest,
    db: Session = Depends(get_db),
) -> dict:
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query 不能为空",
        )
    return serialize_run(create_agent_run(db, query))


@router.get("/runs", response_model=list[AgentSessionRead])
def list_agent_runs(db: Session = Depends(get_db)) -> list[dict]:
    sessions = db.scalars(
        select(AgentSession).order_by(AgentSession.created_at.desc(), AgentSession.id.desc())
    ).all()
    return [serialize_run(session) for session in sessions]


@router.get("/runs/{session_id}", response_model=AgentSessionDetail)
def get_agent_run(session_id: int, db: Session = Depends(get_db)) -> dict:
    return serialize_run(_get_run_or_404(db, session_id), include_details=True)


@router.post(
    "/diagnose",
    response_model=AgentSessionRead,
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
)
def diagnose_compatibility(
    request: DiagnoseRequest,
    db: Session = Depends(get_db),
) -> dict:
    """保留旧路径作为异步运行创建别名，避免客户端静默执行旧固定流程。"""
    return start_agent_run(request, db)


@router.get("/sessions", response_model=list[AgentSessionRead], deprecated=True)
def list_agent_sessions(db: Session = Depends(get_db)) -> list[dict]:
    return list_agent_runs(db)


@router.get(
    "/sessions/{session_id}",
    response_model=AgentSessionDetail,
    deprecated=True,
)
def get_agent_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    return get_agent_run(session_id, db)
