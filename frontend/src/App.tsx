import { useEffect, useState } from "react";
import {
  ApartmentOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Typography } from "antd";

import { AgentDiagnosisPage } from "./pages/AgentDiagnosisPage";
import { AgentTracesPage } from "./pages/AgentTracesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { IncidentReportsPage } from "./pages/IncidentReportsPage";
import { ScenarioLabPage } from "./pages/ScenarioLabPage";
import { TraceViewerPage } from "./pages/TraceViewerPage";
import "./App.css";

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const routes = [
  { key: "/", label: "系统总览", icon: <DashboardOutlined /> },
  { key: "/scenarios", label: "故障模拟", icon: <ExperimentOutlined /> },
  { key: "/agent", label: "Agent 诊断", icon: <RobotOutlined /> },
  { key: "/agent-traces", label: "调用轨迹", icon: <HistoryOutlined /> },
  { key: "/traces", label: "链路追踪", icon: <ApartmentOutlined /> },
  { key: "/incidents", label: "事故报告", icon: <FileTextOutlined /> },
];

function normalizePath(pathname: string) {
  return routes.some((route) => route.key === pathname) ? pathname : "/";
}

function PageContent({ path }: { path: string }) {
  switch (path) {
    case "/scenarios":
      return <ScenarioLabPage />;
    case "/agent":
      return <AgentDiagnosisPage />;
    case "/agent-traces":
      return <AgentTracesPage />;
    case "/traces":
      return <TraceViewerPage />;
    case "/incidents":
      return <IncidentReportsPage />;
    default:
      return <DashboardPage />;
  }
}

function App() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const onPopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath: string) {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  }

  return (
    <Layout className="app-shell">
      <Sider
        width={232}
        collapsible
        collapsed={collapsed}
        trigger={null}
        breakpoint="lg"
        collapsedWidth={0}
        onBreakpoint={(broken) => setCollapsed(broken)}
        className="app-sider"
      >
        <div className="brand"><RobotOutlined /><span>AI SRE Agent</span></div>
        <Menu theme="dark" mode="inline" selectedKeys={[path]} items={routes} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed((value) => !value)} />
          <Text type="secondary">微服务故障诊断与事故分析平台</Text>
        </Header>
        <Content className="app-content"><PageContent path={path} /></Content>
      </Layout>
    </Layout>
  );
}

export default App;
