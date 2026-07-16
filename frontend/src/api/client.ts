import axios from "axios";

import type {
  AgentSession,
  AgentSessionDetail,
  Alert,
  DashboardSummary,
  DiagnoseResponse,
  Incident,
  IncidentReport,
  Metric,
  Approval,
  ScenarioResponse,
  Service,
  TraceDetail,
  TraceSpan,
} from "../types";

interface ApiErrorPayload {
  code?: string;
  message?: string;
  detail?: unknown;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
  timeout: 15_000,
});

export const apiClient = {
  getDashboardSummary: () => api.get<DashboardSummary>("/dashboard/summary"),
  getServices: () => api.get<Service[]>("/services"),
  getAlerts: () => api.get<Alert[]>("/alerts"),
  getMetrics: (metricName?: string) =>
    api.get<Metric[]>("/metrics", { params: { metric_name: metricName } }),
  startAgentRun: (query: string) =>
    api.post<AgentSession>("/agent/runs", { query }),
  getAgentRun: (sessionId: number) =>
    api.get<AgentSessionDetail>("/agent/runs/" + sessionId),
  getAgentRuns: () => api.get<AgentSession[]>("/agent/runs"),
  runScenario: (scenario: string) =>
    api.post<ScenarioResponse>(`/scenarios/${scenario}`),
  diagnose: (query: string) =>
    api.post<DiagnoseResponse>("/agent/diagnose", { query }),
  getAgentSessions: () => api.get<AgentSession[]>("/agent/sessions"),
  getAgentSession: (sessionId: number) =>
    api.get<AgentSessionDetail>(`/agent/sessions/${sessionId}`),
  getTraces: () => api.get<TraceSpan[]>("/traces"),
  getTrace: (traceId: string) => api.get<TraceDetail>(`/traces/${traceId}`),
  getIncidents: () => api.get<Incident[]>("/incidents"),
  getIncident: (incidentId: number) => api.get<Incident>(`/incidents/${incidentId}`),
  getIncidentReport: (incidentId: number) =>
    api.post<IncidentReport>(`/incidents/${incidentId}/report`),
  getApprovals: () => api.get<Approval[]>("/approvals"),
  approveApproval: (approvalId: number) =>
    api.post<Approval>(`/approvals/${approvalId}/approve`),
  rejectApproval: (approvalId: number) =>
    api.post<Approval>(`/approvals/${approvalId}/reject`),
};

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    // 后端统一返回 message；兼容仍使用 FastAPI detail 的旧接口。
    const payload = error.response?.data as ApiErrorPayload | undefined;
    if (typeof payload?.message === "string") return payload.message;
    if (typeof payload?.detail === "string") return payload.detail;
    if (error.code === "ECONNABORTED") return "请求超时，请稍后重试。";
    if (!error.response) return "无法连接后端服务，请确认服务已启动。";
    return `请求失败（HTTP ${error.response.status}）。`;
  }
  return "请求失败，请检查后端服务是否已启动。";
}
