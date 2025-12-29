"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch, getProjectPlanRange } from "../../../lib/api";
import LineChart from "../../../components/LineChart";

export default function ManhoursPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [kpi, setKpi] = useState<any>(null);
  const [series, setSeries] = useState<any>(null);

  async function load(v: FiltersValue) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}${wbs}`;
    const r = await apiFetch(`/reports/kpi${q}`);
    setKpi(r);
    const s = await apiFetch(`/reports/manhours/series${q}&granularity=month`);
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
    <Shell title="Manhours">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-400">Итого manhours (из листа «Люди техника», по умолчанию: qty × {process.env.NEXT_PUBLIC_SHIFT_HOURS || "11"} часов для manpower в факте).</div>
        <div className="text-3xl font-semibold mt-2">{kpi ? Number(kpi.manhours).toFixed(2) : "—"}</div>
      </div>
      <LineChart title="Manhours: план / факт" series={series} />
    </Shell>
  );
}
