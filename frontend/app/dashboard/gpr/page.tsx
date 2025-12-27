"use client";
import { useEffect, useMemo, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch } from "../../../lib/api";

type Operation = {
  id: number;
  project_id: number;
  code: string;
  name: string;
  wbs_path?: string | null;
  discipline?: string | null;
  block?: string | null;
  floor?: string | null;
  ugpr?: string | null;
  unit?: string | null;
  plan_qty_total?: number | null;
  plan_start?: string | null;
  plan_finish?: string | null;
  progress_pct?: number | null;
  critical?: boolean | null;
};

type Dependency = {
  id: number;
  project_id: number;
  predecessor_id: number;
  successor_id: number;
};

const emptyForm = {
  id: null as number | null,
  code: "",
  name: "",
  wbs_path: "",
  discipline: "",
  block: "",
  floor: "",
  ugpr: "",
  unit: "",
  plan_qty_total: "",
  plan_start: "",
  plan_finish: "",
};

function toDate(d: string | null | undefined) {
  if (!d) return null;
  const dt = new Date(d);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function diffDays(a: Date, b: Date) {
  const ms = b.getTime() - a.getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

export default function GprPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { projectId: 1, dateFrom: iso(start), dateTo: iso(today) };
  });
  const [ops, setOps] = useState<Operation[]>([]);
  const [deps, setDeps] = useState<Dependency[]>([]);
  const [criticalPath, setCriticalPath] = useState<number[]>([]);
  const [q, setQ] = useState("");
  const [includeUndated, setIncludeUndated] = useState(true);
  const [groupBy, setGroupBy] = useState<"wbs" | "discipline" | "block" | "floor" | "ugpr">("discipline");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [depFrom, setDepFrom] = useState<number | "">("");
  const [depTo, setDepTo] = useState<number | "">("");

  async function load(v: FiltersValue = filters, qValue = q, undated = includeUndated) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        project_id: String(v.projectId),
        date_from: v.dateFrom,
        date_to: v.dateTo,
        include_undated: String(undated),
      });
      if (qValue.trim()) params.set("q", qValue.trim());
      const data = await apiFetch(`/gpr/gantt?${params.toString()}`);
      setOps(data?.operations || []);
      setDeps(data?.dependencies || []);
      setCriticalPath(data?.critical_path || []);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки операций");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(filters);
  }, []);

  function startEdit(op: Operation) {
    setEditingId(op.id);
    setForm({
      id: op.id,
      code: op.code || "",
      name: op.name || "",
      wbs_path: op.wbs_path || "",
      discipline: op.discipline || "",
      block: op.block || "",
      floor: op.floor || "",
      ugpr: op.ugpr || "",
      unit: op.unit || "",
      plan_qty_total: op.plan_qty_total?.toString() || "",
      plan_start: op.plan_start || "",
      plan_finish: op.plan_finish || "",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm({ ...emptyForm });
  }

  async function saveForm() {
    setError(null);
    const payload: any = {
      project_id: filters.projectId,
      code: form.code.trim(),
      name: form.name.trim(),
      wbs_path: form.wbs_path?.trim() || null,
      discipline: form.discipline?.trim() || null,
      block: form.block?.trim() || null,
      floor: form.floor?.trim() || null,
      ugpr: form.ugpr?.trim() || null,
      unit: form.unit?.trim() || null,
      plan_qty_total: form.plan_qty_total ? Number(form.plan_qty_total) : null,
      plan_start: form.plan_start || null,
      plan_finish: form.plan_finish || null,
    };

    try {
      if (editingId) {
        await apiFetch(`/gpr/operations/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch(`/gpr/operations`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      resetForm();
      await load(filters);
    } catch (e: any) {
      setError(e?.message || "Ошибка сохранения");
    }
  }

  async function removeOperation(id: number) {
    if (!confirm("Удалить операцию?")) return;
    try {
      await apiFetch(`/gpr/operations/${id}`, { method: "DELETE" });
      await load(filters);
    } catch (e: any) {
      setError(e?.message || "Ошибка удаления");
    }
  }

  async function addDependency() {
    if (!depFrom || !depTo) {
      setError("Выберите предшественника и последователя");
      return;
    }
    try {
      await apiFetch("/gpr/dependencies", {
        method: "POST",
        body: JSON.stringify({
          project_id: filters.projectId,
          predecessor_id: depFrom,
          successor_id: depTo,
        }),
      });
      setDepFrom("");
      setDepTo("");
      await load(filters);
    } catch (e: any) {
      setError(e?.message || "Ошибка добавления зависимости");
    }
  }

  async function removeDependency(id: number) {
    if (!confirm("Удалить зависимость?")) return;
    try {
      await apiFetch(`/gpr/dependencies/${id}`, { method: "DELETE" });
      await load(filters);
    } catch (e: any) {
      setError(e?.message || "Ошибка удаления зависимости");
    }
  }

  const gantt = useMemo(() => {
    const start = toDate(filters.dateFrom);
    const end = toDate(filters.dateTo);
    if (!start || !end) return [];
    const total = Math.max(1, diffDays(start, end) + 1);
    return ops
      .map((op) => {
        const s = toDate(op.plan_start);
        const f = toDate(op.plan_finish);
        if (!s || !f) return null;
        if (groupBy === "wbs" && (!op.wbs_path || !op.wbs_path.trim())) return null;
        const startClamp = s < start ? start : s;
        const endClamp = f > end ? end : f;
        if (endClamp < start || startClamp > end) return null;
        const left = (diffDays(start, startClamp) / total) * 100;
        const width = ((diffDays(startClamp, endClamp) + 1) / total) * 100;
        return { op, left, width };
      })
      .filter(Boolean) as { op: Operation; left: number; width: number }[];
  }, [ops, filters.dateFrom, filters.dateTo, groupBy]);

  const ganttGrouped = useMemo(() => {
    const map = new Map<string, { op: Operation; left: number; width: number }[]>();
    for (const row of gantt) {
      let v: string | null | undefined = null;
      if (groupBy === "wbs") v = row.op.wbs_path;
      if (groupBy === "block") v = row.op.block;
      if (groupBy === "ugpr") v = row.op.ugpr;
      const label = v && v.trim() ? v : "—";
      if (!map.has(label)) map.set(label, []);
      map.get(label)!.push(row);
    }
    return Array.from(map.entries())
      .map(([label, rows]) => {
        let minLeft = 100;
        let maxRight = 0;
        for (const r of rows) {
          minLeft = Math.min(minLeft, r.left);
          maxRight = Math.max(maxRight, r.left + r.width);
        }
        const spanLeft = Math.max(0, minLeft);
        const spanWidth = Math.max(0, maxRight - minLeft);
        return { label, rows, spanLeft, spanWidth };
      })
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [gantt, groupBy]);

  const [ganttCollapsed, setGanttCollapsed] = useState<Record<string, boolean>>({});

  function toggleGanttGroup(label: string) {
    setGanttCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  }

  const ganttTicks = useMemo(() => {
    const start = toDate(filters.dateFrom);
    const end = toDate(filters.dateTo);
    if (!start || !end) return [];
    const totalDays = Math.max(1, diffDays(start, end));
    const steps = 6;
    const out = [];
    for (let i = 0; i <= steps; i += 1) {
      const offset = Math.round((totalDays * i) / steps);
      const d = new Date(start.getTime());
      d.setDate(d.getDate() + offset);
      const left = (offset / totalDays) * 100;
      const label = d.toISOString().slice(0, 10);
      out.push({ left, label });
    }
    return out;
  }, [filters.dateFrom, filters.dateTo]);

  const todayMarker = useMemo(() => {
    const start = toDate(filters.dateFrom);
    const end = toDate(filters.dateTo);
    if (!start || !end) return null;
    const today = new Date();
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    if (d < start || d > end) return null;
    const totalDays = Math.max(1, diffDays(start, end));
    const offset = diffDays(start, d);
    const left = (offset / totalDays) * 100;
    return { left, label: d.toISOString().slice(0, 10), date: d };
  }, [filters.dateFrom, filters.dateTo]);

  const grouped = useMemo(() => {
    const key = groupBy;
    const map = new Map<string, Operation[]>();
    for (const op of ops) {
      let v: string | null | undefined = null;
      if (key === "wbs") v = op.wbs_path;
      if (key === "discipline") v = op.discipline;
      if (key === "block") v = op.block;
      if (key === "floor") v = op.floor;
      if (key === "ugpr") v = op.ugpr;
      if (key === "wbs" && (!v || !v.trim())) {
        continue;
      }
      const label = v && v.trim() ? v : "—";
      if (!map.has(label)) map.set(label, []);
      map.get(label)!.push(op);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [ops, groupBy]);

  return (
    <Shell title="ГПР">
      <div className="flex flex-wrap items-end gap-4">
        <Filters
          initial={filters}
          onChange={(v) => {
            setFilters(v);
            load(v);
          }}
        />
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Поиск</div>
          <input
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Код или название"
          />
        </label>
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={includeUndated}
            onChange={(e) => setIncludeUndated(e.target.checked)}
          />
          <span className="text-neutral-400">Показывать без дат</span>
        </label>
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Сортировать по</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as any)}
          >
            <option value="discipline">Дисциплина</option>
            <option value="wbs">WBS</option>
            <option value="block">Блок</option>
            <option value="floor">Этаж</option>
            <option value="ugpr">УГПР</option>
          </select>
        </label>
        <button
          className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm"
          onClick={() => load(filters)}
        >
          Обновить
        </button>
      </div>

      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 p-3">
        <div className="text-sm text-neutral-300 mb-2">Диаграмма Ганта</div>
        <div className="relative h-8 mb-3 bg-neutral-950/60 rounded">
          {ganttTicks.map((t) => (
            <div key={t.label} className="absolute top-1 bottom-1" style={{ left: `${t.left}%` }}>
              <div className="w-px h-full bg-neutral-700" />
              <div className="-translate-x-1/2 text-[10px] text-neutral-400 mt-1 whitespace-nowrap">
                {t.label}
              </div>
            </div>
          ))}
          {todayMarker && (
            <div className="absolute top-0 bottom-0" style={{ left: `${todayMarker.left}%` }}>
              <div className="w-px h-full bg-amber-400" />
              <div className="-translate-x-1/2 text-[10px] text-amber-300 mt-1 whitespace-nowrap">
                Сегодня
              </div>
            </div>
          )}
        </div>
        <div className="space-y-2">
          {ganttGrouped.slice(0, 20).map(({ label, rows, spanLeft, spanWidth }) => (
            <div key={`gantt-${label}`} className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-neutral-300">
                <button
                  className="px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700"
                  onClick={() => toggleGanttGroup(label)}
                  title={ganttCollapsed[label] ? "Развернуть" : "Свернуть"}
                >
                  {ganttCollapsed[label] ? ">" : "v"}
                </button>
                <span className="text-neutral-400">
                  {label} <span className="text-neutral-600">({rows.length})</span>
                </span>
              </div>
              <div className="relative h-6 bg-neutral-950/60 rounded">
                {todayMarker && (
                  <div className="absolute top-0 bottom-0" style={{ left: `${todayMarker.left}%` }}>
                    <div className="w-px h-full bg-amber-400/60" />
                  </div>
                )}
                <div
                  className="absolute top-1 bottom-1 rounded bg-emerald-600/70"
                  style={{ left: `${spanLeft}%`, width: `${spanWidth}%` }}
                  title={`Диапазон: ${label}`}
                />
              </div>
              {!ganttCollapsed[label] &&
                rows.slice(0, 20).map(({ op, left, width }) => (
                  <div key={op.id} className="relative h-7 bg-neutral-950/60 rounded">
                    {todayMarker && (
                      <div className="absolute top-0 bottom-0" style={{ left: `${todayMarker.left}%` }}>
                        <div className="w-px h-full bg-amber-400/50" />
                      </div>
                    )}
                    <div
                      className="absolute top-1 bottom-1 rounded bg-neutral-800"
                      style={{ left: `${left}%`, width: `${width}%` }}
                    />
                    <div
                      className={`absolute top-1 bottom-1 rounded ${
                        op.critical ? "bg-red-500" : "bg-sky-600"
                      }`}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      title={`${op.code} • ${op.name}`}
                    />
                    {typeof op.progress_pct === "number" && (
                      <div
                        className="absolute top-1 bottom-1 rounded bg-emerald-400/80"
                        style={{
                          left: `${left}%`,
                          width: `${(width * Math.max(0, Math.min(100, op.progress_pct))) / 100}%`,
                        }}
                        title={`Прогресс: ${op.progress_pct.toFixed(1)}%`}
                      />
                    )}
                    {todayMarker &&
                      op.plan_start &&
                      op.plan_finish &&
                      todayMarker.date >= toDate(op.plan_start)! &&
                      todayMarker.date <= toDate(op.plan_finish)! && (
                        <div
                          className="absolute -inset-[1px] rounded border border-amber-400/80"
                          style={{ left: `${left}%`, width: `${width}%` }}
                          title="Текущая операция"
                        />
                      )}
                    <div className="absolute left-2 top-1 text-xs text-neutral-200 truncate">
                      {op.code} — {op.name}
                    </div>
                  </div>
                ))}
            </div>
          ))}
          {gantt.length === 0 && (
            <div className="text-xs text-neutral-500">Нет операций с датами в выбранном периоде.</div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">Код</th>
              <th className="text-left px-3 py-2">Название</th>
              <th className="text-left px-3 py-2">WBS</th>
              <th className="text-left px-3 py-2">Блок</th>
              <th className="text-left px-3 py-2">УГПР</th>
              <th className="text-left px-3 py-2">Старт</th>
              <th className="text-left px-3 py-2">Финиш</th>
              <th className="text-right px-3 py-2">План</th>
              <th className="text-right px-3 py-2">Прогресс</th>
              <th className="text-right px-3 py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {grouped.slice(0, 20).map(([label, items]) => (
              <>
                <tr key={`group-${label}`} className="bg-neutral-950/60 text-neutral-300">
                  <td className="px-3 py-2" colSpan={10}>
                    {label} <span className="text-neutral-500">({items.length})</span>
                  </td>
                </tr>
                {items.slice(0, 50).map((op) => (
                  <tr key={op.id} className="border-t border-neutral-800">
                    <td className="px-3 py-2">{op.code}</td>
                    <td className="px-3 py-2">{op.name}</td>
                    <td className="px-3 py-2">{op.wbs_path || "—"}</td>
                    <td className="px-3 py-2">{op.block || "—"}</td>
                    <td className="px-3 py-2">{op.ugpr || "—"}</td>
                    <td className="px-3 py-2">{op.plan_start || "—"}</td>
                    <td className="px-3 py-2">{op.plan_finish || "—"}</td>
                    <td className="px-3 py-2 text-right">
                      {typeof op.plan_qty_total === "number" ? op.plan_qty_total.toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {typeof op.progress_pct === "number" ? `${op.progress_pct.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right space-x-2">
                      <button
                        className="text-sky-400 hover:underline"
                        onClick={() => startEdit(op)}
                      >
                        Изм.
                      </button>
                      <button
                        className="text-red-400 hover:underline"
                        onClick={() => removeOperation(op.id)}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </>
            ))}
            {ops.length === 0 && !loading && (
              <tr>
                <td className="px-3 py-3 text-neutral-500" colSpan={10}>
                  Нет операций для выбранного проекта.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-300 mb-3">Зависимости (FS)</div>
        <div className="flex flex-wrap gap-3 items-end text-sm">
          <label>
            <div className="text-neutral-400 mb-1">Предшественник</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={depFrom}
              onChange={(e) => setDepFrom(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">—</option>
              {ops.map((o) => (
                <option key={`from-${o.id}`} value={o.id}>
                  {o.code} · {o.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div className="text-neutral-400 mb-1">Последователь</div>
            <select
              className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
              value={depTo}
              onChange={(e) => setDepTo(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">—</option>
              {ops.map((o) => (
                <option key={`to-${o.id}`} value={o.id}>
                  {o.code} · {o.name}
                </option>
              ))}
            </select>
          </label>
          <button className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm" onClick={addDependency}>
            Добавить связь
          </button>
        </div>
        <div className="mt-3 rounded border border-neutral-800 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-neutral-950/60 text-neutral-300">
              <tr>
                <th className="text-left px-2 py-2">Предшественник</th>
                <th className="text-left px-2 py-2">Последователь</th>
                <th className="text-right px-2 py-2">Действия</th>
              </tr>
            </thead>
            <tbody>
              {deps.map((d) => {
                const from = ops.find((o) => o.id === d.predecessor_id);
                const to = ops.find((o) => o.id === d.successor_id);
                return (
                  <tr key={`dep-${d.id}`} className="border-t border-neutral-800">
                    <td className="px-2 py-1">
                      {from ? `${from.code} · ${from.name}` : d.predecessor_id}
                    </td>
                    <td className="px-2 py-1">{to ? `${to.code} · ${to.name}` : d.successor_id}</td>
                    <td className="px-2 py-1 text-right">
                      <button className="text-red-400 hover:underline" onClick={() => removeDependency(d.id)}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                );
              })}
              {deps.length === 0 && (
                <tr>
                  <td className="px-2 py-2 text-neutral-500" colSpan={3}>
                    Зависимостей нет.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {criticalPath.length > 0 && (
          <div className="mt-2 text-xs text-neutral-400">
            Критический путь:{" "}
            {criticalPath
              .map((id) => ops.find((o) => o.id === id)?.code || String(id))
              .join(" → ")}
          </div>
        )}
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-300 mb-3">
          {editingId ? "Редактирование операции" : "Новая операция"}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Код"
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
            placeholder="WBS путь"
            value={form.wbs_path}
            onChange={(e) => setForm({ ...form, wbs_path: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Дисциплина"
            value={form.discipline}
            onChange={(e) => setForm({ ...form, discipline: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Блок"
            value={form.block}
            onChange={(e) => setForm({ ...form, block: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="УГПР"
            value={form.ugpr}
            onChange={(e) => setForm({ ...form, ugpr: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="Ед."
            value={form.unit}
            onChange={(e) => setForm({ ...form, unit: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            placeholder="План (qty)"
            value={form.plan_qty_total}
            onChange={(e) => setForm({ ...form, plan_qty_total: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            type="date"
            value={form.plan_start}
            onChange={(e) => setForm({ ...form, plan_start: e.target.value })}
          />
          <input
            className="px-3 py-2 rounded bg-neutral-950 border border-neutral-800"
            type="date"
            value={form.plan_finish}
            onChange={(e) => setForm({ ...form, plan_finish: e.target.value })}
          />
        </div>
        <div className="mt-3 flex gap-2">
          <button
            className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm"
            onClick={saveForm}
          >
            {editingId ? "Сохранить" : "Создать"}
          </button>
          <button
            className="px-4 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm"
            onClick={resetForm}
          >
            Сбросить
          </button>
        </div>
      </div>
    </Shell>
  );
}
