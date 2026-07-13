export type ServiceStatus = "healthy" | "degraded" | "down";
export type Severity = "info" | "warning" | "critical";

export interface DashboardSummary {
  services_total: number;
  services_by_status: Record<string, number>;
  active_alerts: number;
  critical_alerts: number;
  open_incidents: number;
  runbooks_total: number;
  metrics_total: number;
  logs_total: number;
}

export interface Service {
  id: number;
  name: string;
  display_name: string;
  status: ServiceStatus;
  owner: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Alert {
  id: number;
  service_name: string;
  severity: Severity;
  title: string;
  description: string;
  status: "active" | "resolved";
  started_at: string;
  resolved_at: string | null;
  created_at: string;
}

export interface Metric {
  id: number;
  service_name: string;
  metric_name: string;
  metric_value: number;
  unit: string;
  timestamp: string;
  created_at: string;
}

export interface TraceSpan {
  id: number;
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  service_name: string;
  operation_name: string;
  duration_ms: number;
  status: string;
  error_message: string | null;
  timestamp: string;
  created_at: string;
}

export interface TraceDetail {
  trace_id: string;
  spans: TraceSpan[];
}

export interface Incident {
  id: number;
  title: string;
  severity: Severity;
  status: string;
  affected_services: string;
  root_cause: string | null;
  summary: string | null;
  recommendation: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentToolCall {
  id: number;
  session_id: number;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_output: unknown;
  latency_ms: number;
  success: boolean;
  created_at: string;
}

export interface Approval {
  id: number;
  session_id: number;
  action_type: string;
  action_description: string;
  risk_level: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AgentSession {
  id: number;
  user_query: string;
  final_answer: string | null;
  diagnosis_summary: string | null;
  root_cause: string | null;
  recommendation: string | null;
  risk_level: string | null;
  created_at: string;
}

export interface AgentSessionDetail extends AgentSession {
  tool_calls: AgentToolCall[];
  approvals: Approval[];
}

export interface DiagnoseResponse {
  session_id: number;
  final_answer: string;
  root_cause: string;
  recommendation: string;
  risk_level: string;
  evidence: Record<string, unknown>;
  tool_calls: AgentToolCall[];
  approval: Approval | null;
}

export interface ScenarioResponse {
  scenario: string;
  trace_id: string;
  alert: Alert;
  incident: Incident;
  deployment: unknown | null;
  records_created: Record<string, number>;
}
