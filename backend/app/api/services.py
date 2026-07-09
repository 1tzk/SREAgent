from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Service
from app.schemas import ServiceRead


router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db)) -> list[Service]:
    statement = select(Service).order_by(Service.id)
    return list(db.scalars(statement).all())
