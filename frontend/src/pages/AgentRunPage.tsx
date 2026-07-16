import { useEffect, useState } from "react";
import { PlayCircleOutlined, SafetyCertificateOutlined, ToolOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Space, Spin, Tag, Timeline, Typography, message } from "antd";
import TextArea from "antd/es/input/TextArea";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { AgentSessionDetail } from "../types";


const { Title, Text, Paragraph } = Typography;
const questions = [
  "订单接口最近响应很慢，请帮我排查原因。",
  "支付服务出现大量 500 错误，请分析可能原因。",
  "库存服务最近延迟升高，帮我定位根因。",
  "系统错误率突然升高，最近是否和发布有关？",
];
const statusColor: Record<string, string> = {
  queued: "default", running: "processing", completed: "success", failed: "error", stopped: "warning",
};
const stepColor: Record<string, string> = {
  succeeded: "green", failed: "red", rejected: "orange", planned: "blue",
};


export function AgentRunPage() {
  const [query, setQuery] = useState(questions[0]);
  const [run, setRun] = useState<AgentSessionDetail>();
  const [starting, setStarting] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        setRun((await apiClient.getAgentRun(run.id)).data);
      } catch (error) {
        messageApi.error(getApiErrorMessage(error));
      }
    }, 800);
    return () => window.clearTimeout(timer);
  }, [messageApi, run]);

  async function startRun() {
    if (!query.trim()) return messageApi.warning("请输入需要排查的问题。");
    setStarting(true);
    try {
      const created = (await apiClient.startAgentRun(query.trim())).data;
      setRun((await apiClient.getAgentRun(created.id)).data);
      messageApi.success("Agent Run 已入队，将自主选择下一步工具。");
    } catch (error) {
      messageApi.error(getApiErrorMessage(error));
    } finally {
      setStarting(false);
    }
  }

  const active = run && ["queued", "running"].includes(run.status);
  return (
    <section className="page-section">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Title level={2}>自主 Agent 诊断</Title>
          <Text type="secondary">Agent 根据每轮观察结果决定下一步工具；模拟处置受策略白名单约束。</Text>
        </div>
      </div>
      <Card className="diagnosis-input-card">
        <TextArea rows={4} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="描述需要诊断的异常现象" />
        <Space wrap className="quick-question-list">
          {questions.map((item) => <Button key={item} size="small" onClick={() => setQuery(item)}>{item}</Button>)}
        </Space>
        <Button type="primary" icon={<PlayCircleOutlined />} loading={starting} onClick={startRun}>启动 Agent Run</Button>
      </Card>

      {!run && <Card className="empty-workspace"><Empty description="提交问题后查看 Agent 的决策、证据与模拟处置。" /></Card>}
      {run && (
        <Row gutter={[16, 16]} className="content-row">
          <Col span={24}>
            <Card title="运行状态" extra={<Tag color={statusColor[run.status]}>{run.status.toUpperCase()}</Tag>}>
              <Descriptions column={{ xs: 1, md: 3 }} size="small">
                <Descriptions.Item label="Run ID">{run.id}</Descriptions.Item>
                <Descriptions.Item label="轮次">{run.steps_taken} / {run.max_steps}</Descriptions.Item>
                <Descriptions.Item label="问题" span={3}>{run.user_query}</Descriptions.Item>
              </Descriptions>
              {active && <Spin size="small" tip="Agent 正在分析并选择下一步工具…" />}
              {run.failure_reason && <Alert className="content-row" type="warning" showIcon message={run.failure_reason} />}
            </Card>
          </Col>
          <Col xs={24} xl={15}>
            <Card title="最终结论">
              {run.final_answer ? (
                <>
                  <Paragraph className="final-answer">{run.final_answer}</Paragraph>
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="根因">{run.root_cause}</Descriptions.Item>
                    <Descriptions.Item label="建议">{run.recommendation}</Descriptions.Item>
                    <Descriptions.Item label="风险"><Tag>{run.risk_level?.toUpperCase()}</Tag></Descriptions.Item>
                  </Descriptions>
                </>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待 Agent 完成诊断。" />}
            </Card>
          </Col>
          <Col xs={24} xl={9}>
            <Card title={<><SafetyCertificateOutlined /> 模拟处置</>}>
              {run.remediation_executions.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前无需自动处置。" /> : run.remediation_executions.map((item) => (
                <Alert key={item.id} type="info" showIcon message={item.action_type} description={item.service_name + " · " + (item.verified ? "已复查" : "等待复查")} />
              ))}
            </Card>
          </Col>
          <Col span={24}>
            <Card title={<><ToolOutlined /> 自主决策轨迹</>}>
              <Timeline items={run.steps.map((step) => ({
                color: stepColor[step.status],
                children: <div className="tool-timeline-item"><strong>{"#" + step.sequence + " " + (step.tool_name ?? "输出结论")}</strong><Text type="secondary"> · {step.status}</Text><div>{step.rationale}</div></div>,
              }))} />
            </Card>
          </Col>
        </Row>
      )}
    </section>
  );
}
