const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export async function fetchProcedures(params: Record<string, string> = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/procedures?${q}`);
  if (!res.ok) throw new Error("Failed to load procedures");
  return res.json();
}

export async function fetchFines(params: Record<string, string> = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/fines?${q}`);
  if (!res.ok) throw new Error("Failed to load fines");
  return res.json();
}

export async function fetchOffices(params: Record<string, string> = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/offices?${q}`);
  if (!res.ok) throw new Error("Failed to load offices");
  return res.json();
}

export async function fetchAdvisories(params: Record<string, string> = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/advisories?${q}`);
  if (!res.ok) throw new Error("Failed to load advisories");
  return res.json();
}

export async function fetchLegalSections(params: Record<string, string> = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/legal-sections?${q}`);
  if (!res.ok) throw new Error("Failed to load legal sections");
  return res.json();
}

export type LegalUploadPayload = {
  file: File;
  code: string;
  title?: string;
  docType?: string;
  summary?: string;
  issued_by?: string;
  issued_at?: string;
  source_url?: string;
  metadata?: Record<string, unknown> | null;
  token?: string;
  mimeType?: string;
};

export type IngestionJob = {
  id: string;
  status: string;
  progress: number;
  code: string;
  filename: string;
  error_message?: string;
  stats?: {
    sections?: number;
    images?: number;
  };
  document?: Record<string, any> | null;
};

export async function uploadLegalDocument(payload: LegalUploadPayload): Promise<IngestionJob> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("code", payload.code);
  if (payload.title) formData.append("title", payload.title);
  if (payload.docType) formData.append("doc_type", payload.docType);
  if (payload.summary) formData.append("summary", payload.summary);
  if (payload.issued_by) formData.append("issued_by", payload.issued_by);
  if (payload.issued_at) formData.append("issued_at", payload.issued_at);
  if (payload.source_url) formData.append("source_url", payload.source_url);
  if (payload.mimeType) formData.append("mime_type", payload.mimeType);
  if (payload.metadata) formData.append("metadata", JSON.stringify(payload.metadata));

  const headers: Record<string, string> = {};
  if (payload.token) {
    headers["X-Upload-Token"] = payload.token;
  }

  const res = await fetch(`${API_BASE}/legal-documents/upload/`, {
    method: "POST",
    body: formData,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody?.error || "Failed to upload document";
    throw new Error(message);
  }
  return res.json();
}

export async function fetchIngestionJob(jobId: string): Promise<IngestionJob> {
  const res = await fetch(`${API_BASE}/legal-ingestion-jobs/${jobId}/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch ingestion job");
  return res.json();
}

const SESSION_STORAGE_KEY = "chatbot_session_id";

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_STORAGE_KEY);
}

function setSessionId(sessionId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

function clearSessionId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

export async function chat(message: string, sessionId?: string | null, resetSession: boolean = false) {
  // Get session_id from parameter, localStorage, or generate new one
  let currentSessionId = sessionId;
  
  if (resetSession) {
    clearSessionId();
    currentSessionId = null;
  } else if (!currentSessionId) {
    currentSessionId = getSessionId();
  }
  
  const res = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      message,
      session_id: currentSessionId || undefined,
      reset_session: resetSession
    }),
  });
  
  if (!res.ok) throw new Error("Failed to chat");
  
  const data = await res.json();
  
  // Store session_id from response
  if (data.session_id) {
    setSessionId(data.session_id);
  }
  
  return data;
}

export function resetChatSession(): void {
  clearSessionId();
}


