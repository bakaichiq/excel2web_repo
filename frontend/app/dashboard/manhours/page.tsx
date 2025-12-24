"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch } from "../../../lib/api";

export default function ManhoursPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { projectId: 1, dateFrom: iso(start), dateTo: iso(today), wbsPath: "" };
  });
  const [kpi, setKpi] = useState<any>(null);

  async function load(v: FiltersValue) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}${wbs}`;
    const r = await apiFetch(`/reports/kpi${q}`);
    setKpi(r);
  }
  useEffect(()=>{ load(filters); }, []);
  return (
    <Shell title="Manhours">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 p-4">
        <div className="text-sm text-neutral-400">Итого manhours (из листа «Люди техника», по умолчанию: qty × {process.env.NEXT_PUBLIC_SHIFT_HOURS || "11"} часов для manpower в факте).</div>
        <div className="text-3xl font-semibold mt-2">{kpi ? Number(kpi.manhours).toFixed(2) : "—"}</div>
      </div>
    </Shell>
  );
}
