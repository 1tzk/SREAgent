import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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


logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    """统一 API 异常结构，前端可只依赖 code 和 message。"""
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """仅返回字段定位和校验说明，避免将原始请求数据写回响应。"""
    return [
        {
            "field": ".".join(str(part) for part in error.get("loc", [])),
            "message": error.get("msg", "参数不合法"),
            "type": error.get("type", "validation_error"),
        }
        for error in errors
    ]


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        # 保留业务接口抛出的状态码，同时转换为统一错误格式。
        if isinstance(exc.detail, str):
            return _error_response(exc.status_code, "HTTP_ERROR", exc.detail)
        return _error_response(
            exc.status_code,
            "HTTP_ERROR",
            "请求处理失败",
            exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            422,
            "VALIDATION_ERROR",
            "请求参数校验失败",
            _validation_details(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        # 服务端记录完整堆栈，响应只返回安全的通用提示。
        logger.exception("Unhandled API error: %s %s", request.method, request.url.path)
        return _error_response(500, "INTERNAL_ERROR", "服务器内部错误，请稍后重试")

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
