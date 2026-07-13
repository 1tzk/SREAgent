from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.workflow import run_mock_diagnosis, serialize_tool_call
from app.database import get_db
from app.models import AgentSession, AgentToolCall
from app.schemas import (
    AgentSessionDetail,
    AgentSessionRead,
    AgentToolCallRead,
    DiagnoseRequest,
    DiagnoseResponse,
)


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(
    request: DiagnoseRequest,
    db: Session = Depends(get_db),
) -> DiagnoseResponse:
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query 不能为空",
        )
    return DiagnoseResponse.model_validate(
        run_mock_diagnosis(db, request.query.strip())
    )


@router.get("/sessions", response_model=list[AgentSessionRead])
def list_agent_sessions(db: Session = Depends(get_db)) -> list[AgentSession]:
    statement = select(AgentSession).order_by(
        AgentSession.created_at.desc(),
        AgentSession.id.desc(),
    )
    return list(db.scalars(statement).all())


@router.get("/sessions/{session_id}", response_model=AgentSessionDetail)
def get_agent_session(
    session_id: int,
    db: Session = Depends(get_db),
) -> AgentSessionDetail:
    statement = (
        select(AgentSession)
        .options(
            selectinload(AgentSession.tool_calls),
            selectinload(AgentSession.approvals),
        )
        .where(AgentSession.id == session_id)
    )
    session = db.scalar(statement)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定诊断会话",
        )
    return AgentSessionDetail(
        **AgentSessionRead.model_validate(session).model_dump(),
        tool_calls=[
            AgentToolCallRead.model_validate(serialize_tool_call(item))
            for item in sorted(session.tool_calls, key=lambda item: item.id)
        ],
        approvals=session.approvals,
    )


@router.get(
    "/sessions/{session_id}/tool-calls",
    response_model=list[AgentToolCallRead],
)
def list_session_tool_calls(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[AgentToolCallRead]:
    if db.get(AgentSession, session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定诊断会话",
        )
    statement = (
        select(AgentToolCall)
        .where(AgentToolCall.session_id == session_id)
        .order_by(AgentToolCall.id)
    )
    return [
        AgentToolCallRead.model_validate(serialize_tool_call(item))
        for item in db.scalars(statement).all()
    ]
