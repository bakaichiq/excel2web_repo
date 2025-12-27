"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import { apiFetch } from "../../../lib/api";

type Project = {
  id: number;
  code: string;
  name: string;
  description?: string | null;
};

const emptyForm = { code: "", name: "", description: "" };

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/projects");
      setProjects(data || []);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки проектов");
    } finally {
      setLoading(false);
    }
  }

  async function saveProject() {
    setError(null);
    setMsg(null);
    const payload = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description?.trim() || null,
    };
    if (!payload.code || !payload.name) {
      setError("Заполните code и name");
      return;
    }
    try {
      if (editingId) {
        await apiFetch(`/projects/${editingId}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await apiFetch("/projects", { method: "POST", body: JSON.stringify(payload) });
      }
      setForm({ ...emptyForm });
      setEditingId(null);
      setMsg("Проект создан.");
      await load();
    } catch (e: any) {
      setError(e?.message || "Ошибка создания проекта");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Shell title="Проекты">
      <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-300 mb-3">
          {editingId ? "Редактирование проекта" : "Новый проект"}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Код (например PRJ-1)"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Название"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Описание (опционально)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm" onClick={saveProject}>
            {editingId ? "Сохранить" : "Создать"}
          </button>
          <button className="px-4 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm" onClick={load}>
            Обновить
          </button>
          {editingId && (
            <button
              className="px-4 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm"
              onClick={() => {
                setEditingId(null);
                setForm({ ...emptyForm });
              }}
            >
              Отмена
            </button>
          )}
        </div>
        {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
        {msg && <div className="mt-3 text-sm text-neutral-300">{msg}</div>}
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">ID</th>
              <th className="text-left px-3 py-2">Код</th>
              <th className="text-left px-3 py-2">Название</th>
              <th className="text-left px-3 py-2">Описание</th>
              <th className="text-left px-3 py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {(projects || []).map((p) => (
              <tr key={p.id} className="border-t border-neutral-800">
                <td className="px-3 py-2">{p.id}</td>
                <td className="px-3 py-2">{p.code}</td>
                <td className="px-3 py-2">{p.name}</td>
                <td className="px-3 py-2 text-neutral-400">{p.description || "—"}</td>
                <td className="px-3 py-2">
                  <button
                    className="text-sky-400 hover:underline"
                    onClick={() => {
                      setEditingId(p.id);
                      setForm({
                        code: p.code || "",
                        name: p.name || "",
                        description: p.description || "",
                      });
                    }}
                  >
                    Изм.
                  </button>
                </td>
              </tr>
            ))}
            {!loading && projects.length === 0 && (
              <tr>
                <td className="px-3 py-3 text-neutral-500" colSpan={4}>
                  Нет проектов.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
