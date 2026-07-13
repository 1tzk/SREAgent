import { useState } from "react";
import {
  CheckCircleOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Empty,
  Row,
  Space,
  Spin,
  Tag,
  Timeline,
  Typography,
  message,
} from "antd";
import TextArea from "antd/es/input/TextArea";

import { apiClient, getApiErrorMessage } from "../api/client";
import type { DiagnoseResponse } from "../types";

const { Title, Text, Paragraph } = Typography;

const quickQuestions = [
  "订单接口最近响应很慢，请帮我排查原因。",
  "支付服务出现大量 500 错误，请分析可能原因。",
  "库存服务最近延迟升高，帮我定位根因。",
  "系统错误率突然升高，最近是否和发布有关？",
];

const riskColor: Record<string, string> = { high: "red", medium: "gold", low: "green" };

function evidenceCount(evidence: Record<string, unknown>, key: string) {
  const value = evidence[key];
  return Array.isArray(value) ? value.length : 0;
}

function LegacyAgentDiagnosisPage() {
  const [query, setQuery] = useState(quickQuestions[0]);
  const [result, setResult] = useState<DiagnoseResponse>();
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  async function diagnose() {
    if (!query.trim()) {
      messageApi.warning("请输入需要排查的问题。");
      return;
    }
    setLoading(true);
    try {
      setResult((await apiClient.diagnose(query.trim())).data);
      messageApi.success("诊断完成，证据链已保存。");
    } catch (error) {
      messageApi.error(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-section">
      {contextHolder}
      <div className="page-heading"><div><Title level={2}>Agent 诊断</Title><Text type="secondary">确定性 Mock 工作流会检索告警、指标、日志、链路、发布和 Runbook。</Text></div></div>
      <Card className="diagnosis-input-card">
        <TextArea rows={4} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="描述需要诊断的异常现象" />
        <Space wrap className="quick-question-list">
          {quickQuestions.map((item) => <Button key={item} size="small" onClick={() => setQuery(item)}>{item}</Button>)}
        </Space>
        <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={diagnose}>开始诊断</Button>
      </Card>

      {loading && <Spin className="page-spinner" size="large" />}
      {!loading && !result && <Card className="empty-workspace"><Empty description="输入问题后开始一次基于真实证据的诊断。" /></Card>}
      {result && (
        <Row gutter={[16, 16]} className="content-row">
          <Col xs={24} xl={15}>
            <Card title="诊断结论" className="result-card">
              <Paragraph className="final-answer">{result.final_answer}</Paragraph>
              <Divider />
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
                <Descriptions.Item label="根因分析">{result.root_cause}</Descriptions.Item>
                <Descriptions.Item label="风险等级"><Tag color={riskColor[result.risk_level] ?? "blue"}>{result.risk_level.toUpperCase()}</Tag></Descriptions.Item>
                <Descriptions.Item label="修复建议" span={2}>{result.recommendation}</Descriptions.Item>
              </Descriptions>
              <Divider />
              {result.approval ? (
                <Alert type="warning" showIcon icon={<SafetyCertificateOutlined />} message="需要人工审批" description={`已创建 ${result.approval.action_type} 审批单，当前状态：${result.approval.status}`} />
              ) : (
                <Alert type="success" showIcon icon={<CheckCircleOutlined />} message="当前建议无需人工审批" />
              )}
            </Card>
          </Col>
          <Col xs={24} xl={9}>
            <Card title="证据摘要" className="evidence-card">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="相关服务">{Array.isArray(result.evidence.related_services) ? result.evidence.related_services.join("、") : "-"}</Descriptions.Item>
                <Descriptions.Item label="选中链路">{String(result.evidence.selected_trace_id ?? "未找到")}</Descriptions.Item>
                <Descriptions.Item label="告警">{evidenceCount(result.evidence, "alerts")} 条</Descriptions.Item>
                <Descriptions.Item label="指标">{evidenceCount(result.evidence, "metrics")} 个</Descriptions.Item>
                <Descriptions.Item label="日志">{evidenceCount(result.evidence, "logs")} 条</Descriptions.Item>
                <Descriptions.Item label="Span">{evidenceCount(result.evidence, "traces")} 个</Descriptions.Item>
                <Descriptions.Item label="发布记录">{evidenceCount(result.evidence, "deployments")} 条</Descriptions.Item>
                <Descriptions.Item label="Runbook">{evidenceCount(result.evidence, "runbooks")} 篇</Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={24}>
            <Card title={<><ToolOutlined /> 工具调用轨迹</>}>
              <Timeline
                items={result.tool_calls.map((call) => ({
                  color: call.success ? "green" : "red",
                  children: <div className="tool-timeline-item"><strong>{call.tool_name}</strong><Text type="secondary">{call.latency_ms} ms · {call.success ? "success" : "failed"}</Text></div>,
                }))}
              />
            </Card>
          </Col>
        </Row>
      )}
    </section>
  );
}

export { EnhancedAgentDiagnosisPage as AgentDiagnosisPage } from "./AgentDiagnosisEnhanced";
