import { useEffect, useMemo, useState } from "react";
import { ApartmentOutlined } from "@ant-design/icons";
import { Alert, Card, Col, Empty, List, Row, Spin, Tag, Typography } from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { TraceDetail, TraceSpan } from "../types";
import { formatDate } from "./common";

const { Title, Text } = Typography;

export function TraceViewerPage() {
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [detail, setDetail] = useState<TraceDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const traces = useMemo(() => {
    const result = new Map<string, TraceSpan>();
    spans.forEach((span) => {
      if (!result.has(span.trace_id)) result.set(span.trace_id, span);
    });
    return [...result.values()];
  }, [spans]);

  useEffect(() => {
    apiClient.getTraces()
      .then(async ({ data }) => {
        setSpans(data);
        if (data[0]) setDetail((await apiClient.getTrace(data[0].trace_id)).data);
      })
      .catch((requestError) => setError(getApiErrorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);

  async function selectTrace(traceId: string) {
    try {
      setDetail((await apiClient.getTrace(traceId)).data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  if (loading) return <Spin className="page-spinner" size="large" />;
  if (error) return <Alert type="error" showIcon message="链路加载失败" description={error} />;

  return <section className="page-section"><div className="page-heading"><div><Title level={2}>链路追踪</Title><Text type="secondary">从服务调用顺序观察异常请求的耗时与错误位置。</Text></div></div><Row gutter={[16, 16]}><Col xs={24} xl={8}><Card title={<><ApartmentOutlined /> Trace 列表</>} bodyStyle={{ padding: 0 }}>{traces.length === 0 ? <Empty description="暂无链路数据。" /> : <List dataSource={traces} renderItem={(item) => <List.Item className={`session-list-item ${detail?.trace_id === item.trace_id ? "selected" : ""}`} onClick={() => selectTrace(item.trace_id)}><div><strong>{item.trace_id}</strong><div><Text type="secondary">{item.service_name} · {formatDate(item.timestamp)}</Text></div></div></List.Item>} />}</Card></Col><Col xs={24} xl={16}>{detail ? <Card title={`调用链：${detail.trace_id}`}><div className="span-list">{detail.spans.map((span, index) => <div className="span-row" key={span.id}><div className="span-index">{index + 1}</div><div className="span-content"><div><strong>{span.service_name}</strong><Text type="secondary"> · {span.operation_name}</Text></div><div className="span-meta"><Tag color={span.status === "error" ? "red" : "green"}>{span.status}</Tag><Text>{span.duration_ms} ms</Text></div>{span.error_message && <Text type="danger">{span.error_message}</Text>}</div></div>)}</div></Card> : <Card><Empty description="选择一条 Trace 查看调用链。" /></Card>}</Col></Row></section>;
}
