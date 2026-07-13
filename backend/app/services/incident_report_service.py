from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.tools import rank_runbooks
from app.models import Alert, Deployment, Incident, Log, Metric, Trace


def _services(affected_services: str) -> set[str]:
    return {name.strip() for name in affected_services.split(",") if name.strip()}


def _take(items: Iterable[Any], limit: int = 6) -> list[Any]:
    return list(items)[:limit]


def _report_query(incident: Incident) -> str:
    return " ".join(
        part for part in [incident.title, incident.root_cause, incident.summary] if part
    )


def _prevention(incident: Incident) -> str:
    text = _report_query(incident).lower()
    if any(keyword in text for keyword in ("sql", "索引", "库存")):
        return "将 SQL 执行计划和索引检查纳入发布门禁，并对库存查询设置 P95 延迟告警。"
    if any(keyword in text for keyword in ("发布", "回归", "version")):
        return "使用灰度发布和自动回归监控，错误率异常时自动暂停发布批次。"
    if "连接池" in text:
        return "持续监控连接池使用率、长事务和连接泄漏，并定期进行容量压测。"
    if "缓存" in text or "redis" in text:
        return "为缓存连接和命中率设置告警，并在回源压力升高前启用降级策略。"
    return "完善关键接口的错误率和延迟告警，并在发布前执行对应 Runbook 检查。"


def _requires_approval(incident: Incident) -> bool:
    recommendation = (incident.recommendation or "").lower()
    return any(
        keyword in recommendation
        for keyword in ("回滚", "重启", "扩容", "配置", "清理缓存", "rollback", "restart")
    )


def build_incident_report(db: Session, incident: Incident) -> dict[str, Any]:
    services = _services(incident.affected_services)
    logs = _take(
        db.scalars(
            select(Log)
            .where(Log.service_name.in_(services))
            .order_by(Log.timestamp.desc(), Log.id.desc())
        ),
    )
    metrics = _take(
        db.scalars(
            select(Metric)
            .where(Metric.service_name.in_(services))
            .order_by(Metric.timestamp.desc(), Metric.id.desc())
        ),
    )
    trace_ids = {item.trace_id for item in logs if item.trace_id}
    traces = _take(
        db.scalars(
            select(Trace)
            .where(Trace.trace_id.in_(trace_ids))
            .order_by(Trace.timestamp.desc(), Trace.id.desc())
        )
        if trace_ids
        else [],
    )
    deployments = _take(
        db.scalars(
            select(Deployment)
            .where(Deployment.service_name.in_(services))
            .order_by(Deployment.deployed_at.desc(), Deployment.id.desc())
        ),
    )
    alerts = _take(
        db.scalars(
            select(Alert)
            .where(Alert.service_name.in_(services))
            .order_by(Alert.started_at.desc(), Alert.id.desc())
        ),
    )
    runbooks = rank_runbooks(db, _report_query(incident))

    timeline = [
        {
            "occurred_at": incident.created_at,
            "event_type": "incident",
            "title": "事故已创建",
            "description": incident.title,
        }
    ]
    timeline.extend(
        {
            "occurred_at": item.deployed_at,
            "event_type": "deployment",
            "title": f"{item.service_name} 发布 {item.version}",
            "description": item.description,
        }
        for item in deployments
    )
    timeline.extend(
        {
            "occurred_at": item.started_at,
            "event_type": "alert",
            "title": item.title,
            "description": item.description,
        }
        for item in alerts
    )
    timeline.extend(
        {
            "occurred_at": item.timestamp,
            "event_type": "log",
            "title": f"{item.service_name} {item.level}",
            "description": item.message,
        }
        for item in logs[:4]
    )
    timeline.sort(key=lambda item: item["occurred_at"])

    evidence_sources = [
        *[
            {
                "evidence_type": "alert",
                "title": item.title,
                "description": item.description,
                "service_name": item.service_name,
            }
            for item in alerts
        ],
        *[
            {
                "evidence_type": "metric",
                "title": f"{item.metric_name}: {item.metric_value}{item.unit}",
                "description": f"采集时间：{item.timestamp.isoformat()}",
                "service_name": item.service_name,
            }
            for item in metrics
        ],
        *[
            {
                "evidence_type": "log",
                "title": f"{item.level} 日志",
                "description": item.message,
                "service_name": item.service_name,
            }
            for item in logs
        ],
        *[
            {
                "evidence_type": "trace",
                "title": item.operation_name,
                "description": f"{item.duration_ms}ms · {item.status}",
                "service_name": item.service_name,
            }
            for item in traces
        ],
        *[
            {
                "evidence_type": "deployment",
                "title": f"{item.service_name} {item.version}",
                "description": item.description,
                "service_name": item.service_name,
            }
            for item in deployments
        ],
        *[
            {
                "evidence_type": "runbook",
                "title": item["title"],
                "description": f"匹配词：{'、'.join(item['matched_keywords'])}；评分：{item['score']}",
                "service_name": None,
            }
            for item in runbooks
        ],
    ]

    return {
        "incident_id": incident.id,
        "title": incident.title,
        "severity": incident.severity.value,
        "affected_services": sorted(services),
        "timeline": timeline,
        "root_cause": incident.root_cause or "尚未确定，需要结合证据继续定位。",
        "evidence_sources": evidence_sources,
        "recommendation": incident.recommendation or "根据最新证据继续排查并执行相应 Runbook。",
        "prevention": _prevention(incident),
        "requires_approval": _requires_approval(incident),
    }
