export interface ApiHealth {
  status: string;
  judge_configured: boolean;
}

export interface AgentExecution {
  status?: string;
  mode?: string;
  duration_ms?: number;
  fallback?: boolean;
  fallback_reason?: string;
}

export interface AgentTrace {
  agent?: string;
  claim?: string;
  confidence?: number;
  evidence?: Record<string, unknown>;
  recommendations?: string[];
  warnings?: string[];
  execution?: AgentExecution;
}

export interface KnowledgeSource {
  id?: string;
  title?: string;
  source?: string;
  backend?: string;
  score?: number;
  text?: string;
  content?: string;
}

export interface DiagnosisReport {
  crop?: { code?: string; label?: string };
  growth_stage?: string;
  environment?: Record<string, unknown>;
  diagnosis?: string;
  status?: string;
  confidence?: { score?: number; band?: string; meaning?: string };
  candidates?: Array<Record<string, unknown> & { name?: string; confidence?: number }>;
  evidence?: string[];
  differential_analysis?: { alternative?: string; rejection_reason?: string };
  knowledge_sources?: {
    rag_status?: string;
    rag?: KnowledgeSource[];
    kg?: { backend?: string; status?: string };
  };
  risk?: string;
  recommendations?: string[];
  follow_up_questions?: string[];
  request_id?: string;
  judge_mode?: string;
  duration_ms?: number;
  [key: string]: unknown;
}

export interface TraceEvent {
  stage: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
}

export interface DiagnosisTrace {
  trace_id?: string;
  timestamp?: string;
  events?: TraceEvent[];
  [stage: string]: unknown;
}

export interface DiagnosisResult {
  decision: string;
  confidence: number;
  risk_level: string;
  judge_mode: string;
  need_human_review: boolean;
  action_plan: string[];
  traces: AgentTrace[];
  report: DiagnosisReport;
  trace_id?: string;
  trace?: DiagnosisTrace;
  judge_analysis?: Record<string, unknown>;
  status?: string;
}

export interface DecisionSummary {
  id: number;
  created_at: string;
  crop: string;
  intent: string;
  query: string;
  decision: string;
  confidence: number;
  risk_level: string;
  judge_mode: string;
  feedback?: string | null;
}

export interface DecisionDetail extends DecisionSummary {
  action_plan?: string[];
  traces?: AgentTrace[];
  report_json?: DiagnosisReport;
  trace_json?: DiagnosisTrace;
  trace_id?: string;
  need_human_review?: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function requestJson<T>(
  path: string,
  apiKey = "",
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (apiKey) headers.set("X-API-Key", apiKey);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError("无法连接 ACIS API，请检查服务是否启动。", 0);
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "API 请求失败";
    if (response.status === 401) {
      throw new ApiError("API Key 无效，请确认它与本地 ACIS_API_KEY 一致。", 401);
    }
    if (response.status === 503) {
      throw new ApiError("ACIS API 尚未就绪，请检查服务端密钥和依赖状态。", 503);
    }
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

export function getHealth(): Promise<ApiHealth> {
  return requestJson<ApiHealth>("/health");
}

export function getDecisions(apiKey: string): Promise<DecisionSummary[]> {
  return requestJson<DecisionSummary[]>("/decisions?limit=50", apiKey);
}

export function getDecision(apiKey: string, id: number): Promise<DecisionDetail> {
  return requestJson<DecisionDetail>(`/decisions/${id}`, apiKey);
}

export function runDiagnosis(
  apiKey: string,
  query: string,
  options: { useLlmJudge: boolean; useLlmCritic: boolean },
): Promise<DiagnosisResult> {
  return requestJson<DiagnosisResult>("/diagnose", apiKey, {
    method: "POST",
    body: JSON.stringify({
      query,
      use_llm_judge: options.useLlmJudge,
      use_llm_critic: options.useLlmCritic,
    }),
  });
}

export function sendFeedback(
  apiKey: string,
  id: number,
  feedback: "correct" | "incorrect" | "partial",
): Promise<DecisionDetail> {
  return requestJson<DecisionDetail>(`/decisions/${id}/feedback`, apiKey, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
}
