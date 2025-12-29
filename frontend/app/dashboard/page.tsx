"use client";
import { useEffect, useState } from "react";
import Shell from "../../components/Shell";
import Filters, { FiltersValue } from "../../components/Filters";
import KpiCards from "../../components/KpiCards";
import LineChart from "../../components/LineChart";
import { apiFetch, getProjectPlanRange } from "../../lib/api";

export default function Dashboard() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [kpi, setKpi] = useState<any>(null);
  const [series, setSeries] = useState<any>(null);
  const progressPct = Math.max(0, Math.min(100, Number(kpi?.progress_pct ?? 0)));

  async function load(v: FiltersValue) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}${wbs}`;
    const k = await apiFetch(`/reports/kpi${q}`);
    const s = await apiFetch(`/reports/plan-fact/series${q}&granularity=month`);
    setKpi(k);
    setSeries(s);
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
        // fall back to current defaults
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
    <Shell title="Excel2Web">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      <KpiCards kpi={kpi} />
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4 flex items-center gap-4">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center text-sm font-semibold"
            style={{
              background: `conic-gradient(#22c55e ${progressPct}%, #1f2937 0)`,
            }}
          >
            <div className="w-14 h-14 rounded-full bg-neutral-900 flex items-center justify-center text-xs">
              {progressPct.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-sm text-neutral-400">Выполнение плана</div>
            <div className="text-lg font-semibold">{progressPct.toFixed(1)}%</div>
          </div>
        </div>
      </div>
      <LineChart title="План / Факт (месяц)" series={series} />
      <div className="mt-4 text-sm text-neutral-400">
        Экспорт: <a href={`${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/reports/export/plan-fact.xlsx?project_id=${filters.projectId}&date_from=${filters.dateFrom}&date_to=${filters.dateTo}`} target="_blank">Plan-Fact XLSX</a>
        {" · "}
        <a href={`${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/reports/export/kpi.pdf?project_id=${filters.projectId}&date_from=${filters.dateFrom}&date_to=${filters.dateTo}`} target="_blank">KPI PDF</a>
      </div>
    </Shell>
  );
}
