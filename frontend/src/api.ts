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


