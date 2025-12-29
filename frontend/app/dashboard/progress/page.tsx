"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch, getProjectPlanRange } from "../../../lib/api";

export default function ProgressPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [by, setBy] = useState<"wbs"|"discipline"|"block"|"floor"|"ugpr">("discipline");
  const [scenario, setScenario] = useState<"plan" | "forecast" | "actual">("plan");
  const [table, setTable] = useState<any>(null);

  async function load(v: FiltersValue, byKey = by, sc = scenario) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&by=${byKey}&scenario=${sc}${wbs}`;
    const t = await apiFetch(`/reports/plan-fact/table${q}`);
    setTable(t);
  }

  useEffect(() => {
    let ignore = false;
    async function init() {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      const iso = (d: Date) => d.toISOString().slice(0, 10);
      try {
        const r = await getProjectPlanRange(filters.projectId);
        const planStart = r?.plan_start ? String(r.plan_start).slice(0, 10) : null;
        const planFinish = r?.plan_finish ? String(r.plan_finish).slice(0, 10) : null;
        if ((planStart || planFinish) && !ignore) {
          const v = {
            ...filters,
            dateFrom: planStart || iso(start),
            dateTo: planFinish || iso(today),
          };
          setFilters(v);
          await load(v);
          return;
        }
      } catch {
        // ignore
      }
      if (!ignore) {
        const v = { ...filters, dateFrom: iso(start), dateTo: iso(today) };
        setFilters(v);
        await load(v);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <Shell title="Прогресс">
      <div className="flex flex-wrap gap-4 items-end">
        <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Группировка</div>
          <select className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={by}
            onChange={(e)=>{ const v=e.target.value as any; setBy(v); load(filters, v);} }>
            <option value="discipline">Дисциплина</option>
            <option value="wbs">WBS</option>
            <option value="block">Блок</option>
            <option value="floor">Этаж</option>
            <option value="ugpr">УГПР</option>
          </select>
        </label>
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Сценарий</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={scenario}
            onChange={(e) => {
              const v = e.target.value as "plan" | "forecast" | "actual";
              setScenario(v);
              load(filters, by, v);
            }}
          >
            <option value="plan">Plan</option>
            <option value="forecast">Forecast</option>
            <option value="actual">Actual</option>
          </select>
        </label>
      </div>

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">Группа</th>
              <th className="text-right px-3 py-2">План</th>
              <th className="text-right px-3 py-2">Факт</th>
              <th className="text-right px-3 py-2">Отклонение</th>
              <th className="text-right px-3 py-2">Прогресс %</th>
            </tr>
          </thead>
          <tbody>
            {(table?.rows || []).slice(0,50).map((r:any)=>(
              <tr key={r.key} className="border-t border-neutral-800">
                <td className="px-3 py-2">{r.key}</td>
                <td className="px-3 py-2 text-right">{r.plan.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{r.fact.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{r.variance.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{r.progress_pct.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-neutral-500 mt-2">
        План считается по операциям/ГПР; для forecast используется авто‑прогноз по факту (если явного прогноза нет).
      </div>
    </Shell>
  );
}
