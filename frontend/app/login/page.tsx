"use client";
import { useState } from "react";
import { setToken } from "../../lib/api";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [login, setLogin] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl bg-neutral-900 border border-neutral-800 p-6">
        <h1 className="text-xl font-semibold">Вход</h1>
        <p className="text-sm text-neutral-400 mt-1">JWT логин. По умолчанию: admin / admin123 (dev).</p>

        <div className="mt-5 space-y-3">
          <input
            className="w-full px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            placeholder="login"
            autoComplete="username"
          />
          <input
            className="w-full px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            type="password"
            autoComplete="current-password"
          />

          {error && <div className="text-sm text-red-400 whitespace-pre-wrap">{error}</div>}

          <button
            className="w-full px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 disabled:opacity-60"
            disabled={loading}
            onClick={async () => {
              try {
                setError(null);
                setLoading(true);

                const res = await fetch("/api/auth/login", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ login, password }),
                  cache: "no-store",
                });

                if (!res.ok) {
                  const txt = await res.text();
                  throw new Error(txt || `HTTP ${res.status}`);
                }

                const data = await res.json();
                const token = data?.access_token;
                if (!token) throw new Error("В ответе нет access_token");

                setToken(token);
                router.push("/dashboard");
              } catch (e: any) {
                setError(String(e?.message || e));
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? "Входим..." : "Войти"}
          </button>
        </div>
      </div>
    </div>
  );
}
