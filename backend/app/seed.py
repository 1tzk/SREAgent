from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import Log, LogLevel, Metric, Runbook, Service, ServiceStatus


SERVICE_SEED_DATA = [
    {
        "name": "api-gateway",
        "display_name": "API Gateway",
        "owner": "platform-team",
        "description": "统一入口网关，负责请求路由、鉴权和流量控制。",
    },
    {
        "name": "order-service",
        "display_name": "Order Service",
        "owner": "commerce-team",
        "description": "订单创建、订单状态流转和订单查询服务。",
    },
    {
        "name": "payment-service",
        "display_name": "Payment Service",
        "owner": "payment-team",
        "description": "支付请求处理、支付回调和交易状态同步服务。",
    },
    {
        "name": "inventory-service",
        "display_name": "Inventory Service",
        "owner": "supply-chain-team",
        "description": "库存扣减、库存查询和库存同步服务。",
    },
    {
        "name": "user-service",
        "display_name": "User Service",
        "owner": "account-team",
        "description": "用户资料、登录态和账号权限服务。",
    },
]


RUNBOOK_SEED_DATA = [
    {
        "title": "慢 SQL 排查手册",
        "category": "database",
        "tags": "mysql,sql,performance",
        "content": "检查慢查询日志、执行计划、索引命中情况和最近发布变更，确认是否存在全表扫描或锁等待。",
    },
    {
        "title": "Redis 缓存异常处理手册",
        "category": "cache",
        "tags": "redis,cache,availability",
        "content": "检查 Redis 连接、内存使用、淘汰策略、热点 key 和缓存命中率，必要时执行降级或限流。",
    },
    {
        "title": "数据库连接池耗尽处理手册",
        "category": "database",
        "tags": "connection-pool,database,latency",
        "content": "检查连接池使用率、慢请求、长事务和连接泄漏，短期可扩容连接池或重启异常实例。",
    },
    {
        "title": "接口超时排查 SOP",
        "category": "api",
        "tags": "timeout,api,latency",
        "content": "从网关、服务日志、链路追踪和下游依赖四个方向定位耗时阶段，确认是否需要限流或熔断。",
    },
    {
        "title": "服务发布异常与回滚规范",
        "category": "deployment",
        "tags": "deployment,rollback,release",
        "content": "确认发布批次、错误率、关键指标和变更内容；若影响持续扩大，优先执行回滚并保留现场。",
    },
]


NORMAL_METRICS = [
    ("qps", 120.0, "req/s"),
    ("error_rate", 0.12, "%"),
    ("p95_latency", 85.0, "ms"),
    ("cpu_usage", 42.0, "%"),
    ("memory_usage", 58.0, "%"),
    ("db_connection_usage", 35.0, "%"),
    ("cache_hit_rate", 96.5, "%"),
]


def reset_database(db: Session) -> dict[str, int]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    now = datetime.utcnow()
    services = [
        Service(
            status=ServiceStatus.HEALTHY,
            **service_data,
        )
        for service_data in SERVICE_SEED_DATA
    ]
    db.add_all(services)
    db.flush()

    logs: list[Log] = []
    metrics: list[Metric] = []
    for service_index, service_data in enumerate(SERVICE_SEED_DATA):
        service_name = service_data["name"]
        logs.append(
            Log(
                service_name=service_name,
                level=LogLevel.INFO,
                message=f"{service_name} is running normally.",
                trace_id=f"trace-{service_index + 1:04d}",
                timestamp=now - timedelta(minutes=service_index),
            )
        )

        for metric_index, (metric_name, metric_value, unit) in enumerate(NORMAL_METRICS):
            metrics.append(
                Metric(
                    service_name=service_name,
                    metric_name=metric_name,
                    metric_value=metric_value + service_index + metric_index * 0.1,
                    unit=unit,
                    timestamp=now - timedelta(minutes=metric_index),
                )
            )

    runbooks = [Runbook(**runbook_data) for runbook_data in RUNBOOK_SEED_DATA]

    db.add_all(logs)
    db.add_all(metrics)
    db.add_all(runbooks)
    db.commit()

    return {
        "services": len(services),
        "logs": len(logs),
        "metrics": len(metrics),
        "runbooks": len(runbooks),
    }
