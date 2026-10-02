const BASE = "/api/v1";
const TOKEN_KEY = "feedtrace_token";

let token: string | null = null;
try {
  token = localStorage.getItem(TOKEN_KEY);
} catch {
  token = null;
}

export function setToken(value: string | null): void {
  token = value;
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage non disponibile: il token resta solo in memoria */
  }
}

export function hasToken(): boolean {
  return token !== null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(BASE + path, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* corpo non JSON */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface Membership {
  tenant_id: string;
  name: string;
  role: string;
}

export interface Me {
  email: string;
  full_name: string;
  tenant_id: string;
  role: string;
  permissions: string[];
  memberships: Membership[];
}

export interface TokenResponse {
  access_token: string;
  tenant_id: string;
  role: string;
  memberships: Membership[];
}
