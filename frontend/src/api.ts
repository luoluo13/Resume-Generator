import type {
  AiSettings,
  ChatResponse,
  ChatSession,
  ChatSessionSummary,
  ExportResult,
  Resume,
  ResumeSummary,
  SystemInfo,
  TemplateManifest
} from "./types";

export const TEMPLATE_PACK_URL = "/api/templates/pack";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const data = await response.json();
      message = data.detail || data.message || message;
    } catch {
      /* 非 JSON 响应，保留默认提示 */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getResume: () => request<Resume>("/api/resume"),

  saveResume: (resume: Resume) =>
    request<{ savedAt: string }>("/api/resume", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(resume)
    }),

  getTemplates: () => request<TemplateManifest[]>("/api/templates"),

  getInfo: () => request<SystemInfo>("/api/system/info"),

  uploadPhoto: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ path: string; url: string }>("/api/assets/photo", { method: "POST", body: form });
  },

  importJson: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("/api/resume/import", { method: "POST", body: form });
  },

  getAiSettings: () => request<AiSettings>("/api/settings/ai"),

  updateAiSettings: (payload: {
    provider: string;
    baseUrl?: string;
    model?: string;
    apiKey?: string;
    clearKey?: boolean;
  }) =>
    request<AiSettings>("/api/settings/ai", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  testAi: (payload: { provider: string; baseUrl?: string; model?: string; apiKey?: string }) =>
    request<{ ok: boolean; message: string }>("/api/settings/ai/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  getResumes: () =>
    request<{ items: ResumeSummary[]; activeId: string; activeName: string }>("/api/resumes"),

  createResume: (name?: string) =>
    request<{ id: string; name: string; resume: Resume; items: ResumeSummary[]; activeId: string; activeName: string }>(
      "/api/resumes",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || undefined })
      }
    ),

  activateResume: (id: string) =>
    request<{ ok: boolean; activeId: string; activeName: string }>(`/api/resumes/${encodeURIComponent(id)}/activate`, {
      method: "POST"
    }),

  renameResume: (id: string, name: string) =>
    request<{ ok: boolean; item: ResumeSummary; items: ResumeSummary[] }>(
      `/api/resumes/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      }
    ),

  deleteResume: (id: string) =>
    request<{ ok: boolean; activeId: string; activeName: string; items: ResumeSummary[] }>(
      `/api/resumes/${encodeURIComponent(id)}`,
      { method: "DELETE" }
    ),

  getChatSessions: (resumeId?: string) =>
    request<{ items: ChatSessionSummary[] }>(
      `/api/chat/sessions${resumeId ? `?resumeId=${encodeURIComponent(resumeId)}` : ""}`
    ),

  createChatSession: (resumeId: string, title?: string) =>
    request<ChatSession>("/api/chat/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeId, title: title || undefined })
    }),

  getChatSession: (id: string) => request<ChatSession>(`/api/chat/sessions/${encodeURIComponent(id)}`),

  deleteChatSession: (id: string) =>
    request<{ ok: boolean }>(`/api/chat/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),

  chat: (sessionId: string, message: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId, message })
    }),

  confirmChat: (id: string, approve: boolean, sessionId?: string) =>
    request<{
      ok: boolean;
      cancelled: boolean;
      message: string;
      resume: Resume | null;
      resumeId: string;
      session?: ChatSession;
    }>(
      "/api/chat/confirm",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, approve, sessionId })
      }
    ),

  importTemplate: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<TemplateManifest>("/api/templates/import", { method: "POST", body: form });
  },

  deleteTemplate: (id: string) =>
    request<{ ok: boolean }>(`/api/templates/${encodeURIComponent(id)}`, { method: "DELETE" }),

  getTemplatePrompt: async () => {
    const response = await fetch("/api/templates/prompt");
    if (!response.ok) throw new Error(`请求失败（${response.status}）`);
    return response.text();
  },

  exportResume: (format: "pdf" | "png" | "docx", fileName?: string) =>
    request<ExportResult>("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, fileName: fileName || undefined })
    }),

  reveal: (path: string) =>
    request<{ ok: boolean }>("/api/system/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path })
    })
};
