from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Incident
from app.schemas import IncidentRead, IncidentReportResponse
from app.services.incident_report_service import build_incident_report


router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    statement = select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc())
    return list(db.scalars(statement).all())


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定事故",
        )
    return incident


@router.post("/{incident_id}/report", response_model=IncidentReportResponse)
def generate_incident_report(
    incident_id: int,
    db: Session = Depends(get_db),
) -> IncidentReportResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定事故",
        )
    return IncidentReportResponse.model_validate(build_incident_report(db, incident))
