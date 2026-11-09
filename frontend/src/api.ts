import type { ExportResult, Resume, SystemInfo, TemplateManifest } from "./types";

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
