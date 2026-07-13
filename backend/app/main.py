from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.alerts import router as alerts_router
from app.api.approvals import router as approvals_router
from app.api.dashboard import router as dashboard_router
from app.api.deployments import router as deployments_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.logs import router as logs_router
from app.api.metrics import router as metrics_router
from app.api.scenarios import router as scenarios_router
from app.api.seed import router as seed_router
from app.api.services import router as services_router
from app.api.traces import router as traces_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(agent_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(approvals_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(deployments_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(incidents_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(metrics_router, prefix="/api")
    app.include_router(scenarios_router, prefix="/api")
    app.include_router(seed_router, prefix="/api")
    app.include_router(services_router, prefix="/api")
    app.include_router(traces_router, prefix="/api")
    return app


app = create_app()
