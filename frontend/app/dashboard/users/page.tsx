"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import { apiFetch } from "../../../lib/api";

type User = {
  id: number;
  login: string;
  full_name?: string | null;
  role: string;
  is_active?: boolean;
};

const roles = ["Admin", "ПТО", "Финансы", "Руководитель", "Просмотр"];

const emptyForm = {
  login: "",
  full_name: "",
  password: "",
  role: roles[0],
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/admin/users");
      setUsers(data || []);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки пользователей");
    } finally {
      setLoading(false);
    }
  }

  async function createUser() {
    setError(null);
    setMsg(null);
    const payload = {
      login: form.login.trim(),
      full_name: form.full_name?.trim() || null,
      password: form.password,
      role: form.role,
    };
    if (!payload.login || !payload.password) {
      setError("Заполните login и password");
      return;
    }
    try {
      await apiFetch("/admin/users", { method: "POST", body: JSON.stringify(payload) });
      setForm({ ...emptyForm });
      setMsg("Пользователь создан.");
      await load();
    } catch (e: any) {
      setError(e?.message || "Ошибка создания пользователя");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Shell title="Пользователи">
      <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-300 mb-3">Новый пользователь</div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Логин"
            value={form.login}
            onChange={(e) => setForm({ ...form, login: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="ФИО (опционально)"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Пароль"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <select
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm" onClick={createUser}>
            Создать
          </button>
          <button className="px-4 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm" onClick={load}>
            Обновить
          </button>
        </div>
        {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
        {msg && <div className="mt-3 text-sm text-neutral-300">{msg}</div>}
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">ID</th>
              <th className="text-left px-3 py-2">Логин</th>
              <th className="text-left px-3 py-2">ФИО</th>
              <th className="text-left px-3 py-2">Роль</th>
              <th className="text-left px-3 py-2">Активен</th>
            </tr>
          </thead>
          <tbody>
            {(users || []).map((u) => (
              <tr key={u.id} className="border-t border-neutral-800">
                <td className="px-3 py-2">{u.id}</td>
                <td className="px-3 py-2">{u.login}</td>
                <td className="px-3 py-2">{u.full_name || "—"}</td>
                <td className="px-3 py-2">{u.role}</td>
                <td className="px-3 py-2">{u.is_active === false ? "нет" : "да"}</td>
              </tr>
            ))}
            {!loading && users.length === 0 && (
              <tr>
                <td className="px-3 py-3 text-neutral-500" colSpan={5}>
                  Нет пользователей.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
