"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch, getProjectPlanRange } from "../../../lib/api";
import LineChart from "../../../components/LineChart";

function formatM2(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 1 });
}

export default function SalesPlanPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [kpi, setKpi] = useState<any>(null);
  const [series, setSeries] = useState<any>(null);

  async function load(v: FiltersValue) {
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}`;
    const k = await apiFetch(`/reports/sales/kpi${q}`);
    setKpi(k);
    const s = await apiFetch(`/reports/sales/series${q}`);
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
    <Shell title="План продаж">
      <Filters
        initial={filters}
        onChange={(v) => {
          setFilters(v);
          load(v);
        }}
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
        <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
          <div className="text-sm text-neutral-400">План, м²</div>
          <div className="text-2xl font-semibold mt-2">{formatM2(kpi?.plan_m2)}</div>
        </div>
        <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
          <div className="text-sm text-neutral-400">Продано, м²</div>
          <div className="text-2xl font-semibold mt-2">{formatM2(kpi?.sold_m2)}</div>
        </div>
        <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
          <div className="text-sm text-neutral-400">Осталось, м²</div>
          <div className="text-2xl font-semibold mt-2">{formatM2(kpi?.remaining_m2)}</div>
        </div>
        <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
          <div className="text-sm text-neutral-400">Отклонение, м²</div>
          <div className="text-2xl font-semibold mt-2">{formatM2(kpi?.variance_m2)}</div>
          <div className="text-xs text-neutral-500 mt-1">Прогресс: {formatM2(kpi?.progress_pct)}%</div>
        </div>
      </div>

      <LineChart title="План / факт продаж (м²)" series={series} />
    </Shell>
  );
}
