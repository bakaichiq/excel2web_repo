"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch, getProjectPlanRange } from "../../../lib/api";
import ReactECharts from "echarts-for-react";

export default function CashflowPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "" };
  });
  const [data, setData] = useState<any>(null);

  async function load(v: FiltersValue) {
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&scenario=plan`;
    const r = await apiFetch(`/reports/cashflow${q}`);
    setData(r);
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

  const option = {
    title: { text: "Баланс по месяцам", left: "left", textStyle: { color: "#e5e5e5", fontSize: 14 } },
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 20, top: 60, bottom: 30 },
    xAxis: { type: "category", data: (data?.series || []).map((x:any)=>String(x.month).slice(0,10)), axisLabel:{color:"#a3a3a3"} },
    yAxis: { type: "value", axisLabel:{color:"#a3a3a3"} },
    series: [
      { name:"balance", type:"line", data: (data?.series || []).map((x:any)=>x.balance) }
    ]
  };

  return (
    <Shell title="БДДС (Cash Flow)">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-3 mt-4">
        <ReactECharts option={option} style={{ height: 320 }} />
      </div>
    </Shell>
  );
}
