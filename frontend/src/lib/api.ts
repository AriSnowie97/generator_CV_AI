import {
  AIQuotaInfo,
  AISuggestionsResponse,
  BlockKey,
  ProfileData,
  ProfileResponse,
  ResumeLanguage,
  ResumeResponse,
  TemplateId,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "resumecraft_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    let message = `Помилка запиту (${resp.status})`;
    try {
      const errJson = await resp.json();
      if (typeof errJson.detail === "string") {
        message = errJson.detail;
      } else if (Array.isArray(errJson.detail) && errJson.detail[0]?.msg) {
        message = errJson.detail[0].msg;
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new Error(message);
  }

  return resp.json() as Promise<T>;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  verification_token_preview?: string | null;
}

export const api = {
  register: (email: string, password: string, consent_accepted: boolean) =>
    apiFetch<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, consent_accepted }),
    }),

  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  verifyEmail: (token: string) =>
    apiFetch<User>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  googleLogin: (id_token: string, consent_accepted = true) =>
    apiFetch<AuthResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token, consent_accepted }),
    }),

  me: () => apiFetch<User>("/auth/me"),

  getProfile: () => apiFetch<ProfileResponse>("/profile"),

  updateProfile: (data: ProfileData, syncResume = true) =>
    apiFetch<ProfileResponse>(`/profile?sync_resume=${syncResume}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  getResume: () => apiFetch<ResumeResponse>("/resume"),

  updateResume: (payload: {
    title: string;
    template_id: TemplateId;
    language: ResumeLanguage;
    block_order: BlockKey[];
    data: ProfileData;
  }) =>
    apiFetch<ResumeResponse>("/resume", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  syncResumeFromProfile: () =>
    apiFetch<ResumeResponse>("/resume/sync-from-profile", { method: "POST" }),

  getAiQuota: () => apiFetch<AIQuotaInfo>("/ai/quota"),

  improveBullet: (payload: {
    bullet: string;
    role_title: string;
    company: string;
    skills: string[];
    language: ResumeLanguage;
  }) =>
    apiFetch<AISuggestionsResponse>("/ai/improve-bullet", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  generateSummary: (payload: {
    target_role: string;
    experiences_summary: string[];
    skills: string[];
    languages: string[];
    language: ResumeLanguage;
  }) =>
    apiFetch<AISuggestionsResponse>("/ai/generate-summary", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  editSelectedText: (payload: {
    selected_text: string;
    instruction: string;
    language: ResumeLanguage;
  }) =>
    apiFetch<AISuggestionsResponse>("/ai/edit-text", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updatePreferences: (preferred_interface_language: "uk" | "en") =>
    apiFetch<User>("/settings/preferences", {
      method: "PUT",
      body: JSON.stringify({ preferred_interface_language }),
    }),

  exportPersonalData: () => apiFetch<Record<string, unknown>>("/settings/export-data"),

  deleteAccount: () =>
    apiFetch<{ status: string; message: string }>("/settings/account", {
      method: "DELETE",
    }),

  downloadResumeFile: async (payload: {
    format: "pdf" | "docx";
    template_id: TemplateId;
    language: ResumeLanguage;
    block_order: BlockKey[];
    data: ProfileData;
  }): Promise<string> => {
    const token = getStoredToken();
    const resp = await fetch(`${API_BASE}/export`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...payload, use_ai_filename: true }),
    });

    if (!resp.ok) {
      let msg = "Не вдалося експортувати файл";
      try {
        const j = await resp.json();
        if (j.detail) msg = j.detail;
      } catch {
        // ignore
      }
      throw new Error(msg);
    }

    const filename = resp.headers.get("X-Export-Filename") || `ResumeCraft_Resume.${payload.format}`;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return filename;
  },
};
