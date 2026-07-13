from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Approval, ApprovalStatus
from app.schemas import ApprovalRead


router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRead])
def list_approvals(db: Session = Depends(get_db)) -> list[Approval]:
    statement = select(Approval).order_by(
        Approval.created_at.desc(),
        Approval.id.desc(),
    )
    return list(db.scalars(statement).all())


def _update_approval(
    approval_id: int,
    target_status: ApprovalStatus,
    db: Session,
) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定审批单",
        )
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="审批单已处理，不能重复操作",
        )
    approval.status = target_status
    db.commit()
    db.refresh(approval)
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
def approve(
    approval_id: int,
    db: Session = Depends(get_db),
) -> Approval:
    return _update_approval(approval_id, ApprovalStatus.APPROVED, db)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
def reject(
    approval_id: int,
    db: Session = Depends(get_db),
) -> Approval:
    return _update_approval(approval_id, ApprovalStatus.REJECTED, db)
