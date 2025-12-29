"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import MoneyChart from "../../../components/MoneyChart";
import { apiFetch, getProjectPlanRange } from "../../../lib/api";

export default function UgprPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [series, setSeries] = useState<any>(null);
  const [table, setTable] = useState<any>(null);
  const [granularity, setGranularity] = useState<"day" | "week" | "month">("month");
  const [error, setError] = useState<string | null>(null);

  async function load(v: FiltersValue = filters, g = granularity) {
    try {
      setError(null);
      const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
      const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&granularity=${g}${wbs}`;
      const r = await apiFetch(`/reports/ugpr/series${q}`);
      setSeries(r);
      const t = await apiFetch(`/reports/ugpr/table${q.replace(`&granularity=${g}`, "")}`);
      setTable(t);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки УГПР");
    }
  }

  useEffect(() => {
    let ignore = false;
    async function init() {
      const today = new Date();
      const start = new Date(today.getFullYear(), 0, 1);
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
    <Shell title="УГПР">
      <div className="flex flex-wrap items-end gap-4">
        <Filters
          initial={filters}
          onChange={(v) => {
            setFilters(v);
            load(v);
          }}
        />
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Гранулярность</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={granularity}
            onChange={(e) => {
              const g = e.target.value as "day" | "week" | "month";
              setGranularity(g);
              load(filters, g);
            }}
          >
            <option value="day">День</option>
            <option value="week">Неделя</option>
            <option value="month">Месяц</option>
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

      <MoneyChart title="Динамика освоения (сом)" series={series} />

      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">№</th>
              <th className="text-left px-3 py-2">Операция</th>
              <th className="text-right px-3 py-2">План ЖЦП</th>
              <th className="text-right px-3 py-2">Факт ЖЦП</th>
              <th className="text-right px-3 py-2">План период</th>
              <th className="text-right px-3 py-2">Факт период</th>
              <th className="text-right px-3 py-2">План мес</th>
              <th className="text-right px-3 py-2">Факт мес</th>
              <th className="text-right px-3 py-2">План нед</th>
              <th className="text-right px-3 py-2">Факт нед</th>
              <th className="text-right px-3 py-2">План день</th>
              <th className="text-right px-3 py-2">Факт день</th>
            </tr>
          </thead>
          <tbody>
            {(table?.rows || []).slice(0, 200).map((r: any, i: number) => (
              <tr key={`${r.operation_code}-${i}`} className="border-t border-neutral-800">
                <td className="px-3 py-2">{i + 1}</td>
                <td className="px-3 py-2">
                  <div className="text-neutral-200">{r.operation_name}</div>
                  <div className="text-xs text-neutral-500">{r.operation_code}</div>
                </td>
                <td className="px-3 py-2 text-right">{Number(r.plan_lcp).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.fact_lcp).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.plan_period).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.fact_period).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.plan_month).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.fact_month).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.plan_week).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.fact_week).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.plan_day).toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{Number(r.fact_day).toFixed(2)}</td>
              </tr>
            ))}
            {(table?.rows || []).length === 0 && (
              <tr>
                <td className="px-3 py-3 text-neutral-500" colSpan={12}>
                  Нет данных.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
