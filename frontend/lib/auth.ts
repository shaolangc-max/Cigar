// Token 存在 localStorage 里，key 名
const TOKEN_KEY = "cigar_token";
const USER_KEY  = "cigar_user";

export interface AuthUser {
  id: number;
  email: string;
  nickname: string | null;
  avatar_url: string | null;
  subscription_status: string;
  subscription_expires_at: string | null;
  preferred_currency: string;
}

// ── Token 工具 ─────────────────────────────────────────────────────────────

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function saveUser(user: AuthUser) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isPro(): boolean {
  const user = getUser();
  if (!user || user.subscription_status !== "pro") return false;
  if (!user.subscription_expires_at) return false;
  return new Date(user.subscription_expires_at) > new Date();
}

// ── API 调用 ───────────────────────────────────────────────────────────────

function getApiBase(): string {
  if (typeof window !== "undefined") return "/api/v1";
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
}

export async function apiRegister(params: {
  email: string;
  password: string;
  nickname?: string;
  age_confirmed: boolean;
}): Promise<{ access_token: string; subscription_status: string; nickname: string | null }> {
  const res = await fetch(`${getApiBase()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "注册失败");
  return data;
}

export async function apiLogin(params: {
  email: string;
  password: string;
}): Promise<{ access_token: string; subscription_status: string; nickname: string | null }> {
  const res = await fetch(`${getApiBase()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "登录失败");
  return data;
}

export async function apiMe(token: string): Promise<AuthUser> {
  const res = await fetch(`${getApiBase()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "获取用户信息失败");
  return data;
}
