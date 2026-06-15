"use client";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "ho_token";
const REFRESH_KEY = "ho_refresh";
const WS_KEY = "ho_workspace";

export const session = {
  get token() {
    return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY);
  },
  get workspaceId() {
    return typeof window === "undefined" ? null : localStorage.getItem(WS_KEY);
  },
  set(token: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  setWorkspace(id: string) {
    localStorage.setItem(WS_KEY, id);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(WS_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  tenant?: boolean; // envia X-Workspace-Id (default true)
  auth?: boolean; // envia Authorization (default true)
}

export async function api<T = unknown>(
  path: string,
  opts: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, tenant = true, auth = true } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (auth && session.token) headers["Authorization"] = `Bearer ${session.token}`;
  if (tenant && session.workspaceId) headers["X-Workspace-Id"] = session.workspaceId;

  const res = await fetch(`${API_URL}/api/v1${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      (data && (data.detail || data.title)) || `Erro ${res.status}`;
    throw new ApiError(res.status, String(detail));
  }
  return data as T;
}

export const wsUrl = (roomToken: string, workspaceId: string) => {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/ws?token=${encodeURIComponent(roomToken)}&workspace_id=${encodeURIComponent(
    workspaceId
  )}`;
};
