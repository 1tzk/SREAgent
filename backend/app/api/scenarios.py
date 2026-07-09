from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ScenarioResponse
from app.services.scenario_service import ScenarioNotReadyError, run_scenario


router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _run(scenario: str, db: Session) -> ScenarioResponse:
    try:
        result = run_scenario(db, scenario)
    except ScenarioNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ScenarioResponse.model_validate(result)


@router.post("/order-timeout", response_model=ScenarioResponse)
def order_timeout(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("order-timeout", db)


@router.post("/slow-sql", response_model=ScenarioResponse)
def slow_sql(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("slow-sql", db)


@router.post("/payment-500", response_model=ScenarioResponse)
def payment_500(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("payment-500", db)


@router.post("/redis-cache", response_model=ScenarioResponse)
def redis_cache(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("redis-cache", db)


@router.post("/db-pool-exhausted", response_model=ScenarioResponse)
def db_pool_exhausted(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("db-pool-exhausted", db)


@router.post("/release-regression", response_model=ScenarioResponse)
def release_regression(db: Session = Depends(get_db)) -> ScenarioResponse:
    return _run("release-regression", db)
