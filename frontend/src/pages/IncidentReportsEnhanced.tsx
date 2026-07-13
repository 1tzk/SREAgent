import { useEffect, useState } from "react";
import { FileTextOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  List,
  Row,
  Spin,
  Tag,
  Timeline,
  Typography,
} from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { Incident, IncidentReport } from "../types";
import { EmptyState, formatDate, SeverityTag } from "./common";

const { Title, Text } = Typography;
const evidenceColor: Record<string, string> = {
  alert: "red", metric: "blue", log: "orange", trace: "cyan", deployment: "purple", runbook: "green",
};

export function EnhancedIncidentReportsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident>();
  const [report, setReport] = useState<IncidentReport>();
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    apiClient.getIncidents().then(async ({ data }) => {
      setIncidents(data);
      if (data[0]) setSelected((await apiClient.getIncident(data[0].id)).data);
    }).catch((requestError) => setError(getApiErrorMessage(requestError))).finally(() => setLoading(false));
  }, []);

  async function selectIncident(incidentId: number) {
    try {
      setSelected((await apiClient.getIncident(incidentId)).data);
      setReport(undefined);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  async function generateReport() {
    if (!selected) return;
    setReportLoading(true);
    try {
      setReport((await apiClient.getIncidentReport(selected.id)).data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setReportLoading(false);
    }
  }

  if (loading) return <Spin className="page-spinner" size="large" />;
  if (error) return <Alert type="error" showIcon message="事故报告加载失败" description={error} />;

  return <section className="page-section">
    <div className="page-heading"><div><Title level={2}>事故报告</Title><Text type="secondary">基于当前告警、指标、日志、链路、发布和 Runbook 实时生成报告。</Text></div></div>
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8}>
        <Card title={<><FileTextOutlined /> 事故列表</>} bodyStyle={{ padding: 0 }}>
          {incidents.length === 0 ? <EmptyState description="暂无事故报告。" /> : <List dataSource={incidents} renderItem={(item) => <List.Item className={`session-list-item ${selected?.id === item.id ? "selected" : ""}`} onClick={() => selectIncident(item.id)}><div><div><SeverityTag severity={item.severity} /> <strong>{item.title}</strong></div><Text type="secondary">{item.status} · {formatDate(item.created_at)}</Text></div></List.Item>} />}
        </Card>
      </Col>
      <Col xs={24} xl={16}>
        {selected ? <Card title={selected.title} extra={<Button type="primary" loading={reportLoading} onClick={generateReport}>生成完整报告</Button>}>
          <Descriptions column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="严重程度"><SeverityTag severity={selected.severity} /></Descriptions.Item>
            <Descriptions.Item label="状态">{selected.status}</Descriptions.Item>
            <Descriptions.Item label="影响服务" span={2}>{selected.affected_services}</Descriptions.Item>
            <Descriptions.Item label="概要" span={2}>{selected.summary ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="根因" span={2}>{selected.root_cause ?? "尚未确定"}</Descriptions.Item>
          </Descriptions>
          {!report && <div className="report-placeholder"><Empty description="点击“生成完整报告”查看时间线和证据来源。" image={Empty.PRESENTED_IMAGE_SIMPLE} /></div>}
          {report && <div className="report-content">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="根因分析">{report.root_cause}</Descriptions.Item>
              <Descriptions.Item label="修复建议">{report.recommendation}</Descriptions.Item>
              <Descriptions.Item label="预防措施">{report.prevention}</Descriptions.Item>
              <Descriptions.Item label="是否需要审批"><Tag color={report.requires_approval ? "gold" : "green"}>{report.requires_approval ? "需要人工审批" : "无需审批"}</Tag></Descriptions.Item>
            </Descriptions>
            <Title level={5}>事故时间线</Title>
            <Timeline items={report.timeline.map((item) => ({ children: <div><strong>{item.title}</strong><div><Text type="secondary">{formatDate(item.occurred_at)} · {item.event_type}</Text></div><Text>{item.description}</Text></div> }))} />
            <Title level={5}>证据来源</Title>
            <List size="small" bordered dataSource={report.evidence_sources} renderItem={(item) => <List.Item><div className="evidence-source"><div><Tag color={evidenceColor[item.evidence_type]}>{item.evidence_type}</Tag><strong>{item.title}</strong></div><Text type="secondary">{item.service_name ? `${item.service_name} · ` : ""}{item.description}</Text></div></List.Item>} />
          </div>}
        </Card> : <Card><Empty description="选择一个事故查看详情。" /></Card>}
      </Col>
    </Row>
  </section>;
}
