import { Empty, Tag } from "antd";

import type { Severity, ServiceStatus } from "../types";

export const severityColor: Record<Severity, string> = {
  info: "blue",
  warning: "gold",
  critical: "red",
};

export const serviceStatusColor: Record<ServiceStatus, string> = {
  healthy: "green",
  degraded: "gold",
  down: "red",
};

export function SeverityTag({ severity }: { severity: Severity }) {
  return <Tag color={severityColor[severity]}>{severity.toUpperCase()}</Tag>;
}

export function ServiceStatusTag({ status }: { status: ServiceStatus }) {
  return <Tag color={serviceStatusColor[status]}>{status}</Tag>;
}

export function EmptyState({ description }: { description: string }) {
  return <Empty description={description} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
}

export function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-";
}
