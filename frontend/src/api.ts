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
  
  const res = await fetch(`${API_BASE}/chatbot/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      message,
      session_id: currentSessionId || undefined,
      reset_session: resetSession
    }),
    signal: AbortSignal.timeout(600000), // 10 minutes timeout for LLM generation
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

// Legal Document Upload Types
export interface LegalDocument {
  id: number;
  code: string;
  title: string;
  doc_type: string;
  summary?: string;
  issued_by?: string;
  issued_at?: string;
  source_url?: string;
  uploaded_file_url?: string;
  image_count?: number;
  created_at: string;
  updated_at: string;
}

export interface IngestionJob {
  id: string;
  code: string;
  filename: string;
  document: LegalDocument | null;
  metadata: Record<string, any>;
  stats: {
    sections?: number;
    images?: number;
    [key: string]: any;
  };
  status: "pending" | "running" | "completed" | "failed";
  error_message?: string;
  storage_path: string;
  progress: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface UploadLegalDocumentParams {
  file: File;
  code: string;
  title?: string;
  docType?: string;
  summary?: string;
  issuedBy?: string;
  issuedAt?: string;
  sourceUrl?: string;
  mimeType?: string;
  metadata?: Record<string, any>;
  token?: string;
}

export async function uploadLegalDocument(params: UploadLegalDocumentParams): Promise<IngestionJob> {
  const formData = new FormData();
  formData.append("file", params.file);
  formData.append("code", params.code);
  if (params.title) formData.append("title", params.title);
  if (params.docType) formData.append("doc_type", params.docType);
  if (params.summary) formData.append("summary", params.summary);
  if (params.issuedBy) formData.append("issued_by", params.issuedBy);
  if (params.issuedAt) formData.append("issued_at", params.issuedAt);
  if (params.sourceUrl) formData.append("source_url", params.sourceUrl);
  if (params.mimeType) formData.append("mime_type", params.mimeType);
  if (params.metadata) formData.append("metadata", JSON.stringify(params.metadata));

  const headers: HeadersInit = {};
  if (params.token) {
    headers["X-Upload-Token"] = params.token;
  }

  const res = await fetch(`${API_BASE}/legal-documents/upload/`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: "Failed to upload document" }));
    throw new Error(error.error || "Failed to upload document");
  }

  return res.json();
}

export async function fetchIngestionJob(jobId: string): Promise<IngestionJob> {
  const res = await fetch(`${API_BASE}/legal-ingestion-jobs/${jobId}/`);
  if (!res.ok) throw new Error("Failed to fetch ingestion job");
  return res.json();
}

