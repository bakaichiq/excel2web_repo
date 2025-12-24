"use client";

import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import { getToken, apiFetch } from "../../../lib/api";

export default function ImportPage() {
  const [projectId, setProjectId] = useState(1);
  const [imports, setImports] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  async function refresh() {
    try {
      const r = await apiFetch(`/imports?project_id=${projectId}`);
      setImports(r);
    } catch (e: any) {
      setMsg(e?.message || "Ошибка загрузки списка импортов");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function upload(file: File) {
    setMsg(null);

    const token = getToken();
    if (!token) {
      setMsg("Нет токена. Сначала войдите в систему (получите token) и попробуйте снова.");
      return;
    }

    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`/api/imports/upload?project_id=${projectId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      cache: "no-store",
    });

    if (!res.ok) {
      setMsg(await res.text());
      return;
    }

    setMsg("Файл загружен. Импорт запущен.");
    await refresh();
  }

  async function removeImport(id: number) {
    if (!confirm("Удалить импорт и связанные данные?")) return;
    try {
      await apiFetch(`/imports/${id}`, { method: "DELETE" });
      setMsg("Импорт удален.");
      await refresh();
    } catch (e: any) {
      setMsg(e?.message || "Ошибка удаления импорта");
    }
  }

  return (
    <Shell title="Импорт Excel">
      <div className="flex flex-wrap gap-3 items-end">
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Проект ID</div>
          <input
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800 w-32"
            type="number"
            value={projectId}
            onChange={(e) => setProjectId(parseInt(e.target.value || "1", 10))}
          />
        </label>

        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Файл (.xlsx)</div>
          <input
            className="text-sm"
            type="file"
            accept=".xlsx"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
            }}
          />
        </label>
      </div>

      {msg && <div className="mt-3 text-sm text-neutral-300">{msg}</div>}

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">ID</th>
              <th className="text-left px-3 py-2">Файл</th>
              <th className="text-left px-3 py-2">Статус</th>
              <th className="text-left px-3 py-2">Создан</th>
              <th className="text-left px-3 py-2">Загружено строк</th>
              <th className="text-left px-3 py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((r: any) => (
              <tr key={r.id} className="border-t border-neutral-800">
                <td className="px-3 py-2">{r.id}</td>
                <td className="px-3 py-2">{r.file_name}</td>
                <td className="px-3 py-2">{r.status}</td>
                <td className="px-3 py-2">
                  {String(r.created_at).slice(0, 19).replace("T", " ")}
                </td>
                <td className="px-3 py-2">{r.rows_loaded ?? "—"}</td>
                <td className="px-3 py-2">
                  <button
                    className="text-red-400 hover:underline"
                    onClick={() => removeImport(r.id)}
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-neutral-500 mt-2">
        Обновляй страницу, чтобы увидеть завершение импорта (MVP). Потом добавим WebSocket/поллинг.
      </div>
    </Shell>
  );
}
