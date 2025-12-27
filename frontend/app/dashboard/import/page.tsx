"use client";

import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import { getToken, apiFetch } from "../../../lib/api";

export default function ImportPage() {
  const [projectId, setProjectId] = useState(1);
  const [imports, setImports] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [errorsByRun, setErrorsByRun] = useState<Record<number, any[]>>({});
  const [openErrors, setOpenErrors] = useState<Record<number, boolean>>({});
  const [compareRunA, setCompareRunA] = useState<number | null>(null);
  const [compareRunB, setCompareRunB] = useState<number | null>(null);
  const [compareBy, setCompareBy] = useState<"wbs" | "discipline" | "block" | "floor" | "ugpr">("wbs");
  const [compareScenario, setCompareScenario] = useState<"plan" | "forecast" | "actual">("plan");
  const [compareDateFrom, setCompareDateFrom] = useState<string>(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
  });
  const [compareDateTo, setCompareDateTo] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [compareResult, setCompareResult] = useState<any>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  async function refresh() {
    try {
      const r = await apiFetch(`/imports?project_id=${projectId}`);
      setImports(r);
    } catch (e: any) {
      setMsg(e?.message || "Ошибка загрузки списка импортов");
    }
  }

  async function loadErrors(importRunId: number) {
    try {
      const r = await apiFetch(`/imports/${importRunId}/errors`);
      setErrorsByRun((prev) => ({ ...prev, [importRunId]: r || [] }));
    } catch (e: any) {
      setMsg(e?.message || "Ошибка загрузки ошибок импорта");
    }
  }

  async function toggleErrors(importRunId: number) {
    const isOpen = !!openErrors[importRunId];
    if (!isOpen && !errorsByRun[importRunId]) {
      await loadErrors(importRunId);
    }
    setOpenErrors((prev) => ({ ...prev, [importRunId]: !isOpen }));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    if (imports.length >= 2) {
      setCompareRunA(imports[0].id);
      setCompareRunB(imports[1].id);
    } else if (imports.length === 1) {
      setCompareRunA(imports[0].id);
      setCompareRunB(null);
    } else {
      setCompareRunA(null);
      setCompareRunB(null);
    }
  }, [imports]);

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

  async function runCompare() {
    setCompareError(null);
    setCompareResult(null);
    if (!compareRunA || !compareRunB) {
      setCompareError("Выберите две версии для сравнения.");
      return;
    }
    if (compareRunA === compareRunB) {
      setCompareError("Нужно выбрать разные версии.");
      return;
    }
    try {
      const q = new URLSearchParams({
        project_id: String(projectId),
        run_a: String(compareRunA),
        run_b: String(compareRunB),
        date_from: compareDateFrom,
        date_to: compareDateTo,
        by: compareBy,
        scenario: compareScenario,
      });
      const r = await apiFetch(`/imports/compare?${q.toString()}`);
      setCompareResult(r);
    } catch (e: any) {
      setCompareError(e?.message || "Ошибка сравнения импортов");
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
              <>
                <tr key={r.id} className="border-t border-neutral-800">
                  <td className="px-3 py-2">{r.id}</td>
                  <td className="px-3 py-2">{r.file_name}</td>
                  <td className="px-3 py-2">{r.status}</td>
                  <td className="px-3 py-2">
                    {String(r.created_at).slice(0, 19).replace("T", " ")}
                  </td>
                  <td className="px-3 py-2">{r.rows_loaded ?? "—"}</td>
                  <td className="px-3 py-2 space-x-3">
                    <button
                      className="text-sky-400 hover:underline"
                      onClick={() => toggleErrors(r.id)}
                    >
                      {openErrors[r.id] ? "Скрыть ошибки" : "Ошибки"}
                    </button>
                    <button
                      className="text-red-400 hover:underline"
                      onClick={() => removeImport(r.id)}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
                {openErrors[r.id] && (
                  <tr className="border-t border-neutral-800 bg-neutral-950/40">
                    <td className="px-3 py-2" colSpan={6}>
                      <div className="text-xs text-neutral-400 mb-2">Ошибки импорта</div>
                      <div className="rounded border border-neutral-800 overflow-hidden">
                        <table className="w-full text-xs">
                          <thead className="bg-neutral-950/60 text-neutral-300">
                            <tr>
                              <th className="text-left px-2 py-1">Лист</th>
                              <th className="text-left px-2 py-1">Строка</th>
                              <th className="text-left px-2 py-1">Колонка</th>
                              <th className="text-left px-2 py-1">Сообщение</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(errorsByRun[r.id] || []).map((er: any, i: number) => (
                              <tr key={`${r.id}-err-${i}`} className="border-t border-neutral-800">
                                <td className="px-2 py-1">{er.sheet || "—"}</td>
                                <td className="px-2 py-1">{er.row_num ?? "—"}</td>
                                <td className="px-2 py-1">{er.column || "—"}</td>
                                <td className="px-2 py-1 text-neutral-200">{er.message}</td>
                              </tr>
                            ))}
                            {(errorsByRun[r.id] || []).length === 0 && (
                              <tr>
                                <td className="px-2 py-2 text-neutral-500" colSpan={4}>
                                  Ошибок не найдено.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-neutral-500 mt-2">
        Обновляй страницу, чтобы увидеть завершение импорта (MVP). Потом добавим WebSocket/поллинг.
      </div>

      <div className="mt-6 rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-300 mb-3">Сравнение версий</div>
        <div className="flex flex-wrap gap-3 items-end text-sm">
          <label>
            <div className="text-neutral-400 mb-1">Версия A</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={compareRunA ?? ""}
              onChange={(e) => setCompareRunA(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">—</option>
              {imports.map((r) => (
                <option key={`a-${r.id}`} value={r.id}>
                  {r.id} · {r.file_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div className="text-neutral-400 mb-1">Версия B</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={compareRunB ?? ""}
              onChange={(e) => setCompareRunB(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">—</option>
              {imports.map((r) => (
                <option key={`b-${r.id}`} value={r.id}>
                  {r.id} · {r.file_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div className="text-neutral-400 mb-1">С</div>
            <input
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              type="date"
              value={compareDateFrom}
              onChange={(e) => setCompareDateFrom(e.target.value)}
            />
          </label>
          <label>
            <div className="text-neutral-400 mb-1">По</div>
            <input
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              type="date"
              value={compareDateTo}
              onChange={(e) => setCompareDateTo(e.target.value)}
            />
          </label>
          <label>
            <div className="text-neutral-400 mb-1">Группировка</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={compareBy}
              onChange={(e) => setCompareBy(e.target.value as any)}
            >
              <option value="wbs">WBS</option>
              <option value="discipline">Дисциплина</option>
              <option value="block">Блок</option>
              <option value="floor">Этаж</option>
              <option value="ugpr">УГПР</option>
            </select>
          </label>
          <label>
            <div className="text-neutral-400 mb-1">Сценарий</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={compareScenario}
              onChange={(e) => setCompareScenario(e.target.value as any)}
            >
              <option value="plan">Plan</option>
              <option value="forecast">Forecast</option>
              <option value="actual">Actual</option>
            </select>
          </label>
          <button className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm" onClick={runCompare}>
            Сравнить
          </button>
        </div>
        {compareError && <div className="mt-3 text-sm text-red-400">{compareError}</div>}
        {compareResult && (
          <div className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div className="rounded bg-neutral-950 border border-neutral-800 p-3">
                <div className="text-neutral-400">Fact qty Δ</div>
                <div className="text-lg font-semibold">{compareResult.kpi.delta.fact_qty.toFixed(2)}</div>
              </div>
              <div className="rounded bg-neutral-950 border border-neutral-800 p-3">
                <div className="text-neutral-400">Plan qty Δ</div>
                <div className="text-lg font-semibold">{compareResult.kpi.delta.plan_qty.toFixed(2)}</div>
              </div>
              <div className="rounded bg-neutral-950 border border-neutral-800 p-3">
                <div className="text-neutral-400">Progress Δ</div>
                <div className="text-lg font-semibold">{compareResult.kpi.delta.progress_pct.toFixed(2)}%</div>
              </div>
            </div>

            <div className="mt-4 rounded border border-neutral-800 overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-neutral-950/60 text-neutral-300">
                  <tr>
                    <th className="text-left px-2 py-2">Группа</th>
                    <th className="text-right px-2 py-2">Fact A</th>
                    <th className="text-right px-2 py-2">Fact B</th>
                    <th className="text-right px-2 py-2">Δ Fact</th>
                    <th className="text-right px-2 py-2">Plan A</th>
                    <th className="text-right px-2 py-2">Plan B</th>
                    <th className="text-right px-2 py-2">Δ Plan</th>
                    <th className="text-right px-2 py-2">Δ Prog%</th>
                  </tr>
                </thead>
                <tbody>
                  {compareResult.table.rows.slice(0, 50).map((r: any) => (
                    <tr key={`cmp-${r.key}`} className="border-t border-neutral-800">
                      <td className="px-2 py-1">{r.key}</td>
                      <td className="px-2 py-1 text-right">{Number(r.a.fact).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.b.fact).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.delta.fact).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.a.plan).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.b.plan).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.delta.plan).toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{Number(r.delta.progress_pct).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}
