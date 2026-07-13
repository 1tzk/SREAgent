import { useEffect, useState } from "react";
import { FileTextOutlined } from "@ant-design/icons";
import { Alert, Card, Col, Descriptions, Empty, List, Row, Spin, Typography } from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { Incident } from "../types";
import { EmptyState, formatDate, SeverityTag } from "./common";

const { Title, Text } = Typography;

export function IncidentReportsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    apiClient.getIncidents()
      .then(async ({ data }) => {
        setIncidents(data);
        if (data[0]) setSelected((await apiClient.getIncident(data[0].id)).data);
      })
      .catch((requestError) => setError(getApiErrorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);

  async function selectIncident(incidentId: number) {
    try {
      setSelected((await apiClient.getIncident(incidentId)).data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  if (loading) return <Spin className="page-spinner" size="large" />;
  if (error) return <Alert type="error" showIcon message="事故报告加载失败" description={error} />;

  return <section className="page-section"><div className="page-heading"><div><Title level={2}>事故报告</Title><Text type="secondary">统一查看模拟场景产生的事故影响、根因和处理建议。</Text></div></div><Row gutter={[16, 16]}><Col xs={24} xl={8}><Card title={<><FileTextOutlined /> 事故列表</>} bodyStyle={{ padding: 0 }}>{incidents.length === 0 ? <EmptyState description="暂无事故报告。" /> : <List dataSource={incidents} renderItem={(item) => <List.Item className={`session-list-item ${selected?.id === item.id ? "selected" : ""}`} onClick={() => selectIncident(item.id)}><div><div><SeverityTag severity={item.severity} /> <strong>{item.title}</strong></div><Text type="secondary">{item.status} · {formatDate(item.created_at)}</Text></div></List.Item>} />}</Card></Col><Col xs={24} xl={16}>{selected ? <Card title={selected.title}><Descriptions column={1} size="small"><Descriptions.Item label="严重程度"><SeverityTag severity={selected.severity} /></Descriptions.Item><Descriptions.Item label="状态">{selected.status}</Descriptions.Item><Descriptions.Item label="影响服务">{selected.affected_services}</Descriptions.Item><Descriptions.Item label="概要">{selected.summary ?? "-"}</Descriptions.Item><Descriptions.Item label="根因">{selected.root_cause ?? "尚未确定"}</Descriptions.Item><Descriptions.Item label="处理建议">{selected.recommendation ?? "-"}</Descriptions.Item><Descriptions.Item label="创建时间">{formatDate(selected.created_at)}</Descriptions.Item></Descriptions></Card> : <Card><Empty description="选择一个事故查看详情。" /></Card>}</Col></Row></section>;
}
