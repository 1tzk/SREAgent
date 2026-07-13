import { useState } from "react";
import { ExperimentOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Row, Typography, message } from "antd";

import { apiClient, getApiErrorMessage } from "../api/client";

const { Title, Paragraph, Text } = Typography;

const scenarios = [
  { key: "order-timeout", title: "模拟订单接口超时", detail: "提高订单服务延迟并写入超时链路。" },
  { key: "slow-sql", title: "模拟库存服务慢 SQL", detail: "生成慢 SQL、缺失索引和近期发布证据。" },
  { key: "payment-500", title: "模拟支付服务 500 错误", detail: "提高错误率并生成错误调用链。" },
  { key: "redis-cache", title: "模拟 Redis 缓存异常", detail: "降低缓存命中率并产生超时日志。" },
  { key: "db-pool-exhausted", title: "模拟数据库连接池耗尽", detail: "让多个服务等待数据库连接。" },
  { key: "release-regression", title: "模拟服务发布异常", detail: "写入版本回归、错误率和回滚建议。" },
];

export function ScenarioLabPage() {
  const [running, setRunning] = useState<string>();
  const [messageApi, contextHolder] = message.useMessage();

  async function runScenario(key: string) {
    setRunning(key);
    try {
      const { data } = await apiClient.runScenario(key);
      messageApi.success(`场景已生成：${data.alert.title}`);
    } catch (error) {
      messageApi.error(getApiErrorMessage(error));
    } finally {
      setRunning(undefined);
    }
  }

  return (
    <section className="page-section">
      {contextHolder}
      <div className="page-heading"><div><Title level={2}>故障模拟实验室</Title><Text type="secondary">每次操作都会向本地演示数据库写入可用于诊断的真实证据链。</Text></div></div>
      <Alert className="scenario-notice" type="info" showIcon message="建议先执行种子初始化" description="场景依赖 services 基础数据；重置数据可调用 POST /api/seed/reset。" />
      <Row gutter={[16, 16]}>
        {scenarios.map((scenario) => (
          <Col xs={24} md={12} xl={8} key={scenario.key}>
            <Card className="scenario-card" title={<><ExperimentOutlined /> {scenario.title}</>}>
              <Paragraph type="secondary">{scenario.detail}</Paragraph>
              <Button type="primary" block loading={running === scenario.key} onClick={() => runScenario(scenario.key)}>运行场景</Button>
            </Card>
          </Col>
        ))}
      </Row>
    </section>
  );
}
