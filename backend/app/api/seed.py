from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SeedResetResponse
from app.seed import reset_database


router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/reset", response_model=SeedResetResponse)
def reset_seed_data(db: Session = Depends(get_db)) -> SeedResetResponse:
    result = reset_database(db)
    return SeedResetResponse(status="ok", **result)
