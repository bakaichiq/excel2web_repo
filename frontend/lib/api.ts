// lib/api.ts

const IS_SERVER = typeof window === "undefined";

const APP_ORIGIN =
  process.env.NEXT_PUBLIC_APP_ORIGIN ||
  process.env.APP_ORIGIN ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

function buildUrl(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  const url = `/api${p}`;
  return IS_SERVER ? new URL(url, APP_ORIGIN).toString() : url;
}

function normalizeToken(raw: string | null): string | null {
  if (!raw) return null;
  const t = raw.trim();
  if (!t) return null;
  // если кто-то сохранил "Bearer xxx" — извлечём xxx
  if (/^bearer\s+/i.test(t)) return t.replace(/^bearer\s+/i, "").trim();
  return t;
}

export function getToken(): string | null {
  if (IS_SERVER) return null;
  return normalizeToken(localStorage.getItem("token"));
}

export function setToken(t: string) {
  const norm = normalizeToken(t) || "";
  localStorage.setItem("token", norm);
}

export function clearToken() {
  localStorage.removeItem("token");
}

export async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(opts.headers || undefined);

  const isFormData = typeof FormData !== "undefined" && opts.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(buildUrl(path), { ...opts, headers, cache: "no-store" });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `HTTP ${res.status} ${res.statusText}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.blob();
}

// ✅ Логин через JSON: {login, password}
// Ответ: {access_token, token_type}
export async function login(loginValue: string, password: string) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: loginValue, password }),
    cache: "no-store",
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || res.statusText);
  }

  const data = await res.json();
  const token = normalizeToken(data?.access_token);

  if (!token) throw new Error("В ответе нет access_token");

  setToken(token);
  return data;
}

export async function getProjectPlanRange(projectId: number) {
  return apiFetch(`/projects/${projectId}/plan-range`);
}
