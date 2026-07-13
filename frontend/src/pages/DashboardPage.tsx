import { useEffect, useMemo, useState } from "react";
import {
  AlertOutlined,
  ApiOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Alert, Card, Col, List, Row, Spin, Statistic, Typography } from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { DashboardSummary, Metric, Service, Alert as AlertItem } from "../types";
import { EmptyState, formatDate, ServiceStatusTag, SeverityTag } from "./common";

const { Title, Text } = Typography;

function averageLatestMetric(metrics: Metric[], metricName: string) {
  const latest = new Map<string, Metric>();
  metrics
    .filter((item) => item.metric_name === metricName)
    .forEach((item) => {
      const previous = latest.get(item.service_name);
      if (!previous || new Date(item.timestamp) > new Date(previous.timestamp)) {
        latest.set(item.service_name, item);
      }
    });
  const values = [...latest.values()].map((item) => item.metric_value);
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary>();
  const [services, setServices] = useState<Service[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    Promise.all([
      apiClient.getDashboardSummary(),
      apiClient.getServices(),
      apiClient.getAlerts(),
      apiClient.getMetrics(),
    ])
      .then(([summaryResult, serviceResult, alertResult, metricResult]) => {
        setSummary(summaryResult.data);
        setServices(serviceResult.data);
        setAlerts(alertResult.data);
        setMetrics(metricResult.data);
      })
      .catch((requestError) => setError(getApiErrorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);

  const averageP95 = useMemo(() => averageLatestMetric(metrics, "p95_latency"), [metrics]);
  const averageErrorRate = useMemo(
    () => averageLatestMetric(metrics, "error_rate"),
    [metrics],
  );

  if (loading) return <Spin className="page-spinner" size="large" />;
  if (error) return <Alert type="error" showIcon message="数据加载失败" description={error} />;

  return (
    <section className="page-section">
      <div className="page-heading">
        <div>
          <Title level={2}>系统总览</Title>
          <Text type="secondary">实时汇总服务健康度、告警与核心性能指标。</Text>
        </div>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card"><Statistic title="服务数量" value={summary?.services_total ?? 0} prefix={<ApiOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card"><Statistic title="活跃告警" value={summary?.active_alerts ?? 0} valueStyle={{ color: "#d48806" }} prefix={<AlertOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card"><Statistic title="严重告警" value={summary?.critical_alerts ?? 0} valueStyle={{ color: "#cf1322" }} prefix={<WarningOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card"><Statistic title="平均 P95 延迟" value={averageP95} precision={0} suffix="ms" prefix={<ClockCircleOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className="metric-card"><Statistic title="平均错误率" value={averageErrorRate} precision={2} suffix="%" prefix={<WarningOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="content-row">
        <Col xs={24} xl={14}>
          <div className="section-heading"><Title level={4}>服务状态</Title></div>
          {services.length === 0 ? <EmptyState description="暂无服务数据，请先初始化种子数据。" /> : (
            <Row gutter={[12, 12]}>
              {services.map((service) => (
                <Col xs={24} md={12} key={service.id}>
                  <Card size="small" className="service-card">
                    <div className="service-card-top"><strong>{service.display_name}</strong><ServiceStatusTag status={service.status} /></div>
                    <Text type="secondary">{service.description}</Text>
                    <div className="service-owner">负责人：{service.owner}</div>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Col>
        <Col xs={24} xl={10}>
          <div className="section-heading"><Title level={4}>最近告警</Title></div>
          <Card className="list-card" bodyStyle={{ padding: 0 }}>
            {alerts.length === 0 ? <EmptyState description="当前没有告警。" /> : (
              <List
                dataSource={alerts}
                renderItem={(item) => (
                  <List.Item className="alert-list-item">
                    <div><div className="item-title"><SeverityTag severity={item.severity} />{item.title}</div><Text type="secondary">{item.service_name} · {formatDate(item.started_at)}</Text></div>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </section>
  );
}
