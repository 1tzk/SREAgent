from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Deployment,
    DeploymentStatus,
    Incident,
    Log,
    LogLevel,
    Metric,
    Service,
    ServiceStatus,
    Trace,
)


class ScenarioNotReadyError(RuntimeError):
    pass


def _trace_id(scenario: str) -> str:
    return f"{scenario}-{uuid4().hex[:16]}"


def _metric(
    service_name: str,
    metric_name: str,
    metric_value: float,
    unit: str,
    timestamp: datetime,
) -> Metric:
    return Metric(
        service_name=service_name,
        metric_name=metric_name,
        metric_value=metric_value,
        unit=unit,
        timestamp=timestamp,
    )


def _log(
    service_name: str,
    level: LogLevel,
    message: str,
    trace_id: str,
    timestamp: datetime,
) -> Log:
    return Log(
        service_name=service_name,
        level=level,
        message=message,
        trace_id=trace_id,
        timestamp=timestamp,
    )


def _span(
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    service_name: str,
    operation_name: str,
    duration_ms: float,
    timestamp: datetime,
    status: str = "ok",
    error_message: str | None = None,
) -> Trace:
    return Trace(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        service_name=service_name,
        operation_name=operation_name,
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
        timestamp=timestamp,
    )


def _ensure_services(db: Session, service_names: set[str]) -> None:
    # 日志和指标通过服务名关联 services，造数前先给出可操作的初始化提示。
    existing = set(
        db.scalars(select(Service.name).where(Service.name.in_(service_names))).all()
    )
    missing = sorted(service_names - existing)
    if missing:
        raise ScenarioNotReadyError(
            f"缺少基础服务数据：{', '.join(missing)}，请先调用 POST /api/seed/reset"
        )


def _save_scenario(
    db: Session,
    scenario: str,
    affected_services: set[str],
    alert: Alert,
    incident: Incident,
    logs: list[Log],
    metrics: list[Metric],
    traces: list[Trace],
    deployment: Deployment | None = None,
) -> dict:
    _ensure_services(db, affected_services)

    # 故障证据写入的同时标记受影响服务，保证仪表盘状态与场景一致。
    services = db.scalars(
        select(Service).where(Service.name.in_(affected_services))
    ).all()
    for service in services:
        service.status = ServiceStatus.DEGRADED

    records = [alert, incident, *logs, *metrics, *traces]
    if deployment is not None:
        records.append(deployment)
    # 一个场景的所有证据一次提交，避免 Agent 读取到不完整的故障上下文。
    db.add_all(records)
    db.commit()

    db.refresh(alert)
    db.refresh(incident)
    if deployment is not None:
        db.refresh(deployment)

    return {
        "scenario": scenario,
        "trace_id": traces[0].trace_id,
        "alert": alert,
        "incident": incident,
        "deployment": deployment,
        "records_created": {
            "alerts": 1,
            "incidents": 1,
            "logs": len(logs),
            "metrics": len(metrics),
            "traces": len(traces),
            "deployments": int(deployment is not None),
        },
    }


def simulate_order_timeout(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("order-timeout")
    alert = Alert(
        service_name="order-service",
        severity=AlertSeverity.CRITICAL,
        title="订单接口超时率持续升高",
        description="order-service P95 延迟超过 3 秒，网关已观察到请求超时。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=3),
    )
    incident = Incident(
        title="订单创建接口大面积超时",
        severity=AlertSeverity.CRITICAL,
        status="open",
        affected_services="api-gateway,order-service",
        root_cause=None,
        summary="订单创建链路延迟突增，order-service span 占据主要耗时。",
        recommendation="检查订单服务线程池及下游依赖，必要时限流并扩容。",
    )
    logs = [
        _log(
            "order-service",
            LogLevel.WARN,
            "request timeout: POST /orders exceeded 3000ms, downstream inventory pending",
            trace_id,
            now - timedelta(seconds=25),
        ),
        _log(
            "api-gateway",
            LogLevel.ERROR,
            "upstream timeout from order-service after 3500ms",
            trace_id,
            now - timedelta(seconds=22),
        ),
    ]
    metrics = [
        _metric(
            "order-service", "p95_latency", 420.0, "ms", now - timedelta(minutes=5)
        ),
        _metric(
            "order-service", "p95_latency", 1850.0, "ms", now - timedelta(minutes=2)
        ),
        _metric("order-service", "p95_latency", 3680.0, "ms", now),
        _metric("order-service", "error_rate", 8.6, "%", now),
    ]
    traces = [
        _span(trace_id, "span-01", None, "api-gateway", "POST /api/orders", 3725, now),
        _span(
            trace_id,
            "span-02",
            "span-01",
            "order-service",
            "POST /orders",
            3610,
            now,
            "error",
            "context deadline exceeded",
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "inventory-service",
            "reserve inventory",
            640,
            now,
        ),
    ]
    return _save_scenario(
        db,
        "order-timeout",
        {"api-gateway", "order-service", "inventory-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
    )


def simulate_slow_sql(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("slow-sql")
    alert = Alert(
        service_name="inventory-service",
        severity=AlertSeverity.CRITICAL,
        title="库存查询出现慢 SQL",
        description="inventory-service 查询耗时超过 4 秒，并影响订单链路。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=8),
    )
    incident = Incident(
        title="库存服务慢 SQL 导致订单链路延迟",
        severity=AlertSeverity.CRITICAL,
        status="investigating",
        affected_services="inventory-service,order-service",
        root_cause="库存查询缺少 sku_id 与 warehouse_id 联合索引。",
        summary="inventory-service 发布后出现全表扫描，订单服务同步等待库存结果。",
        recommendation="补充联合索引，核对执行计划，并评估回滚最近发布。",
    )
    deployment = Deployment(
        service_name="inventory-service",
        version="v1.8.3",
        operator="supply-chain-release",
        description="优化库存批量查询逻辑。",
        status=DeploymentStatus.SUCCESS,
        deployed_at=now - timedelta(minutes=35),
    )
    logs = [
        _log(
            "inventory-service",
            LogLevel.WARN,
            "slow SQL detected duration=4280ms rows_examined=184203",
            trace_id,
            now - timedelta(seconds=45),
        ),
        _log(
            "inventory-service",
            LogLevel.ERROR,
            "missing index on inventory(sku_id, warehouse_id); query timeout",
            trace_id,
            now - timedelta(seconds=42),
        ),
        _log(
            "order-service",
            LogLevel.WARN,
            "inventory-service response slow, order confirmation delayed",
            trace_id,
            now - timedelta(seconds=39),
        ),
    ]
    metrics = [
        _metric(
            "inventory-service", "p95_latency", 210.0, "ms", now - timedelta(minutes=10)
        ),
        _metric(
            "inventory-service", "p95_latency", 2240.0, "ms", now - timedelta(minutes=4)
        ),
        _metric("inventory-service", "p95_latency", 4520.0, "ms", now),
        _metric("order-service", "p95_latency", 2380.0, "ms", now),
        _metric("inventory-service", "cpu_usage", 88.0, "%", now),
    ]
    traces = [
        _span(trace_id, "span-01", None, "api-gateway", "POST /api/orders", 3300, now),
        _span(
            trace_id, "span-02", "span-01", "order-service", "confirm order", 3180, now
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "inventory-service",
            "SELECT inventory availability",
            4520,
            now,
            "error",
            "query timeout after 4s",
        ),
    ]
    return _save_scenario(
        db,
        "slow-sql",
        {"api-gateway", "order-service", "inventory-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
        deployment,
    )


def simulate_payment_500(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("payment-500")
    alert = Alert(
        service_name="payment-service",
        severity=AlertSeverity.CRITICAL,
        title="支付接口 500 错误率突增",
        description="payment-service 5xx 错误率升至 27%，支付链路失败。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=4),
    )
    incident = Incident(
        title="支付服务返回大量 500",
        severity=AlertSeverity.CRITICAL,
        status="open",
        affected_services="payment-service,order-service",
        root_cause=None,
        summary="支付确认请求在 payment-service 内部异常终止。",
        recommendation="检查支付渠道响应与异常堆栈，临时切换备用通道。",
    )
    logs = [
        _log(
            "payment-service",
            LogLevel.ERROR,
            "HTTP 500 POST /payments: NullPointerException while parsing provider response",
            trace_id,
            now - timedelta(seconds=18),
        ),
        _log(
            "order-service",
            LogLevel.ERROR,
            "payment confirmation failed: upstream payment-service returned 500",
            trace_id,
            now - timedelta(seconds=16),
        ),
    ]
    metrics = [
        _metric("payment-service", "error_rate", 0.4, "%", now - timedelta(minutes=6)),
        _metric("payment-service", "error_rate", 12.5, "%", now - timedelta(minutes=2)),
        _metric("payment-service", "error_rate", 27.3, "%", now),
        _metric("payment-service", "qps", 186.0, "req/s", now),
    ]
    traces = [
        _span(trace_id, "span-01", None, "api-gateway", "POST /api/payments", 510, now),
        _span(
            trace_id, "span-02", "span-01", "order-service", "confirm payment", 455, now
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "payment-service",
            "POST /payments",
            390,
            now,
            "error",
            "HTTP 500: provider response parse failed",
        ),
    ]
    return _save_scenario(
        db,
        "payment-500",
        {"api-gateway", "order-service", "payment-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
    )


def simulate_redis_cache(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("redis-cache")
    alert = Alert(
        service_name="user-service",
        severity=AlertSeverity.WARNING,
        title="Redis 缓存命中率显著下降",
        description="user-service 缓存命中率降至 31%，接口延迟持续升高。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=6),
    )
    incident = Incident(
        title="Redis 异常引发用户接口延迟",
        severity=AlertSeverity.WARNING,
        status="investigating",
        affected_services="user-service,order-service",
        root_cause="Redis 节点连接不稳定，大量请求回源数据库。",
        summary="cache miss 与 redis timeout 同时增加，用户和订单查询延迟上升。",
        recommendation="检查 Redis 节点健康和连接数，启用本地缓存与降级策略。",
    )
    logs = [
        _log(
            "user-service",
            LogLevel.WARN,
            "redis timeout after 800ms key=user:profile:7842",
            trace_id,
            now - timedelta(seconds=32),
        ),
        _log(
            "order-service",
            LogLevel.WARN,
            "cache miss rate high for user-order-summary, fallback to database",
            trace_id,
            now - timedelta(seconds=29),
        ),
    ]
    metrics = [
        _metric(
            "user-service", "cache_hit_rate", 95.8, "%", now - timedelta(minutes=8)
        ),
        _metric(
            "user-service", "cache_hit_rate", 58.4, "%", now - timedelta(minutes=3)
        ),
        _metric("user-service", "cache_hit_rate", 31.2, "%", now),
        _metric("user-service", "p95_latency", 1480.0, "ms", now),
        _metric("order-service", "p95_latency", 920.0, "ms", now),
    ]
    traces = [
        _span(
            trace_id, "span-01", None, "api-gateway", "GET /api/users/7842", 1620, now
        ),
        _span(
            trace_id, "span-02", "span-01", "user-service", "GET /users/7842", 1535, now
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "user-service",
            "Redis GET user:profile:7842",
            805,
            now,
            "error",
            "redis command timeout",
        ),
        _span(
            trace_id,
            "span-04",
            "span-02",
            "user-service",
            "database fallback",
            680,
            now,
        ),
    ]
    return _save_scenario(
        db,
        "redis-cache",
        {"api-gateway", "user-service", "order-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
    )


def simulate_db_pool_exhausted(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("db-pool-exhausted")
    alert = Alert(
        service_name="order-service",
        severity=AlertSeverity.CRITICAL,
        title="数据库连接池接近耗尽",
        description="order-service 数据库连接使用率达到 99%，多个服务请求排队。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=5),
    )
    incident = Incident(
        title="共享数据库连接池耗尽",
        severity=AlertSeverity.CRITICAL,
        status="open",
        affected_services="order-service,inventory-service,user-service",
        root_cause="长事务占用连接，连接池无可用连接。",
        summary="多个服务等待数据库连接，P95 延迟同步升高。",
        recommendation="终止异常长事务，检查连接泄漏，并临时调整连接池容量。",
    )
    logs = [
        _log(
            "order-service",
            LogLevel.ERROR,
            "connection pool exhausted: timeout waiting for connection pool_size=50 active=50",
            trace_id,
            now - timedelta(seconds=28),
        ),
        _log(
            "inventory-service",
            LogLevel.ERROR,
            "database connection acquisition timeout after 2000ms",
            trace_id,
            now - timedelta(seconds=25),
        ),
        _log(
            "user-service",
            LogLevel.WARN,
            "request queued: no database connection available",
            trace_id,
            now - timedelta(seconds=21),
        ),
    ]
    metrics = [
        _metric("order-service", "db_connection_usage", 99.2, "%", now),
        _metric("inventory-service", "db_connection_usage", 97.8, "%", now),
        _metric("user-service", "db_connection_usage", 96.5, "%", now),
        _metric("order-service", "p95_latency", 4250.0, "ms", now),
        _metric("inventory-service", "p95_latency", 3680.0, "ms", now),
        _metric("user-service", "p95_latency", 2740.0, "ms", now),
    ]
    traces = [
        _span(trace_id, "span-01", None, "api-gateway", "POST /api/orders", 4480, now),
        _span(
            trace_id, "span-02", "span-01", "order-service", "create order", 4350, now
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "order-service",
            "acquire database connection",
            3010,
            now,
            "error",
            "connection pool exhausted",
        ),
        _span(
            trace_id,
            "span-04",
            "span-02",
            "inventory-service",
            "reserve stock",
            2520,
            now,
        ),
    ]
    return _save_scenario(
        db,
        "db-pool-exhausted",
        {"api-gateway", "order-service", "inventory-service", "user-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
    )


def simulate_release_regression(db: Session) -> dict:
    now = datetime.utcnow()
    trace_id = _trace_id("release-regression")
    alert = Alert(
        service_name="user-service",
        severity=AlertSeverity.CRITICAL,
        title="新版本发布后错误率回归",
        description="user-service v2.4.0 发布后错误率由 0.3% 升至 18%。",
        status=AlertStatus.ACTIVE,
        started_at=now - timedelta(minutes=12),
    )
    incident = Incident(
        title="user-service v2.4.0 发布回归",
        severity=AlertSeverity.CRITICAL,
        status="investigating",
        affected_services="user-service,api-gateway",
        root_cause="v2.4.0 用户配置兼容逻辑存在空值处理缺陷。",
        summary="错误率上升时间与新版本发布时间高度吻合。",
        recommendation="回滚至 v2.3.6，并补充旧配置兼容测试。",
    )
    deployment = Deployment(
        service_name="user-service",
        version="v2.4.0",
        operator="account-release",
        description="上线用户偏好配置重构。",
        status=DeploymentStatus.SUCCESS,
        deployed_at=now - timedelta(minutes=15),
    )
    logs = [
        _log(
            "user-service",
            LogLevel.ERROR,
            "new version regression detected: profile preferences schema incompatible",
            trace_id,
            now - timedelta(seconds=36),
        ),
        _log(
            "user-service",
            LogLevel.WARN,
            "rollback suggested for version v2.4.0 due to elevated 5xx rate",
            trace_id,
            now - timedelta(seconds=31),
        ),
        _log(
            "api-gateway",
            LogLevel.ERROR,
            "user-service upstream returned 500 for GET /users/profile",
            trace_id,
            now - timedelta(seconds=27),
        ),
    ]
    metrics = [
        _metric("user-service", "error_rate", 0.3, "%", now - timedelta(minutes=18)),
        _metric("user-service", "error_rate", 7.8, "%", now - timedelta(minutes=10)),
        _metric("user-service", "error_rate", 18.2, "%", now),
        _metric("user-service", "p95_latency", 1120.0, "ms", now),
    ]
    traces = [
        _span(
            trace_id,
            "span-01",
            None,
            "api-gateway",
            "GET /api/users/profile",
            1190,
            now,
        ),
        _span(
            trace_id,
            "span-02",
            "span-01",
            "user-service",
            "GET /users/profile",
            1080,
            now,
            "error",
            "profile preferences schema incompatible",
        ),
        _span(
            trace_id,
            "span-03",
            "span-02",
            "user-service",
            "map profile preferences",
            760,
            now,
            "error",
            "unexpected null preference value",
        ),
    ]
    return _save_scenario(
        db,
        "release-regression",
        {"api-gateway", "user-service"},
        alert,
        incident,
        logs,
        metrics,
        traces,
        deployment,
    )


SCENARIO_HANDLERS: dict[str, Callable[[Session], dict]] = {
    "order-timeout": simulate_order_timeout,
    "slow-sql": simulate_slow_sql,
    "payment-500": simulate_payment_500,
    "redis-cache": simulate_redis_cache,
    "db-pool-exhausted": simulate_db_pool_exhausted,
    "release-regression": simulate_release_regression,
}


def run_scenario(db: Session, scenario: str) -> dict:
    try:
        return SCENARIO_HANDLERS[scenario](db)
    except Exception:
        # 场景中任一记录写入失败时回滚整个事务，保持证据链一致。
        db.rollback()
        raise
