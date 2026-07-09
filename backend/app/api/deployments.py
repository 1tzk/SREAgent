from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deployment
from app.schemas import DeploymentRead

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("", response_model=list[DeploymentRead])
def list_deployments(
    service_name: str | None = None,
    db: Session = Depends(get_db),
) -> list[Deployment]:
    statement = select(Deployment)
    if service_name:
        statement = statement.where(Deployment.service_name == service_name)
    statement = statement.order_by(Deployment.deployed_at.desc(), Deployment.id.desc())
    return list(db.scalars(statement).all())
