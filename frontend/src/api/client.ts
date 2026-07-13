import axios from "axios";

import type {
  AgentSession,
  AgentSessionDetail,
  Alert,
  DashboardSummary,
  DiagnoseResponse,
  Incident,
  Metric,
  ScenarioResponse,
  Service,
  TraceDetail,
  TraceSpan,
} from "../types";

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
};

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail ?? error.message;
  }
  return "请求失败，请检查后端服务是否已启动。";
}
