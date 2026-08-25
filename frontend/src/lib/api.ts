import type {
  ActivityEntry,
  Analytics,
  AuthResponse,
  Conversation,
  ConversationDetail,
  Draft,
  Integration,
  KnowledgeSource,
  Organization,
  SendResult,
  User,
  WebhookDelivery,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";
export const TOKEN_KEY = "leadops_access_token";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export function readToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = readToken();
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    let message = response.statusText || "Request failed";
    try {
      const data = (await response.json()) as { detail?: string };
      message = data.detail || message;
    } catch {
      // The response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  register: (payload: Record<string, string>) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { organization_slug: string; email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => request<AuthResponse>("/api/auth/me"),

  analytics: () => request<Analytics>("/api/analytics"),
  conversations: (status = "all", search = "") => {
    const params = new URLSearchParams({ status });
    if (search) params.set("search", search);
    return request<Conversation[]>(`/api/conversations?${params}`);
  },
  conversation: (id: string) => request<ConversationDetail>(`/api/conversations/${id}`),
  regenerateDraft: (id: string) =>
    request<Draft>(`/api/conversations/${id}/draft`, { method: "POST" }),
  updateDraft: (id: string, body: string) =>
    request<Draft>(`/api/conversations/${id}/draft`, {
      method: "PATCH",
      body: JSON.stringify({ body }),
    }),
  approveDraft: (id: string) =>
    request<Draft>(`/api/conversations/${id}/approve`, { method: "POST" }),
  sendDraft: (id: string) =>
    request<SendResult>(`/api/conversations/${id}/send`, { method: "POST" }),
  assign: (id: string, userId: string | null) =>
    request<Conversation>(`/api/conversations/${id}/assignment`, {
      method: "PATCH",
      body: JSON.stringify({ user_id: userId }),
    }),
  escalate: (id: string, userId: string | null, note: string) =>
    request<Conversation>(`/api/conversations/${id}/escalate`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, note: note || null }),
    }),

  knowledge: () => request<KnowledgeSource[]>("/api/knowledge"),
  uploadPdf: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<KnowledgeSource>("/api/knowledge/files", { method: "POST", body: form });
  },
  addUrl: (url: string, title?: string) =>
    request<KnowledgeSource>("/api/knowledge/urls", {
      method: "POST",
      body: JSON.stringify({ url, title: title || null }),
    }),
  addText: (title: string, content: string) =>
    request<KnowledgeSource>("/api/knowledge/text", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    }),
  deleteKnowledge: (id: string) =>
    request<void>(`/api/knowledge/${id}`, { method: "DELETE" }),

  integrations: () => request<Integration[]>("/api/integrations"),
  configureCrm: (payload: Record<string, unknown>) =>
    request<Integration>("/api/integrations/crm", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testCrm: () => request<Integration>("/api/integrations/crm/test", { method: "POST" }),
  configureN8n: (payload: Record<string, unknown>) =>
    request<Integration>("/api/integrations/n8n", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  webhooks: () => request<WebhookDelivery[]>("/api/webhooks"),
  retryWebhook: (id: string) =>
    request<WebhookDelivery>(`/api/webhooks/${id}/retry`, { method: "POST" }),
  activity: (level = "all") => request<ActivityEntry[]>(`/api/activity?level=${level}`),

  organization: () => request<Organization>("/api/organization"),
  updateOrganization: (name: string) =>
    request<Organization>("/api/organization", {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  members: () => request<User[]>("/api/organization/members"),
  createMember: (payload: Record<string, unknown>) =>
    request<User>("/api/organization/members", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export async function publicRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(payload.detail || "Request failed", response.status);
  }
  return (await response.json()) as T;
}
