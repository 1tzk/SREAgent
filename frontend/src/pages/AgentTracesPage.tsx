import { useEffect, useState } from "react";
import { HistoryOutlined } from "@ant-design/icons";
import { Alert, Card, Col, Empty, List, Row, Spin, Tag, Typography } from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { AgentSession, AgentSessionDetail } from "../types";
import { formatDate } from "./common";

const { Title, Text, Paragraph } = Typography;

export function AgentTracesPage() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [selected, setSelected] = useState<AgentSessionDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    apiClient.getAgentSessions()
      .then(async ({ data }) => {
        setSessions(data);
        if (data[0]) setSelected((await apiClient.getAgentSession(data[0].id)).data);
      })
      .catch((requestError) => setError(getApiErrorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);

  async function selectSession(sessionId: number) {
    try {
      setSelected((await apiClient.getAgentSession(sessionId)).data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  if (loading) return <Spin className="page-spinner" size="large" />;
  if (error) return <Alert type="error" showIcon message="会话加载失败" description={error} />;

  return <section className="page-section"><div className="page-heading"><div><Title level={2}>Agent 调用轨迹</Title><Text type="secondary">查看历史诊断会话及其工具调用审计记录。</Text></div></div><Row gutter={[16, 16]}><Col xs={24} xl={8}><Card title={<><HistoryOutlined /> 诊断会话</>} bodyStyle={{ padding: 0 }}>{sessions.length === 0 ? <Empty description="暂无诊断会话。" /> : <List dataSource={sessions} renderItem={(item) => <List.Item className={`session-list-item ${selected?.id === item.id ? "selected" : ""}`} onClick={() => selectSession(item.id)}><div><strong>#{item.id} {item.user_query}</strong><div><Text type="secondary">{formatDate(item.created_at)}</Text></div></div></List.Item>} />}</Card></Col><Col xs={24} xl={16}>{selected ? <Card title={`会话 #${selected.id}`}><Paragraph><Text type="secondary">用户问题</Text><br />{selected.user_query}</Paragraph><Paragraph><Text type="secondary">最终回答</Text><br />{selected.final_answer ?? "-"}</Paragraph><Paragraph><Text type="secondary">根因</Text><br />{selected.root_cause ?? "-"}</Paragraph><Paragraph><Text type="secondary">建议</Text><br />{selected.recommendation ?? "-"}</Paragraph><div className="tool-call-chips">{selected.tool_calls.map((call) => <Tag key={call.id} color={call.success ? "green" : "red"}>{call.tool_name} · {call.latency_ms}ms</Tag>)}</div></Card> : <Card><Empty description="选择一个诊断会话查看详情。" /></Card>}</Col></Row></section>;
}
