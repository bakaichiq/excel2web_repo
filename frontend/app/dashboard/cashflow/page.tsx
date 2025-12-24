"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch } from "../../../lib/api";
import ReactECharts from "echarts-for-react";

export default function CashflowPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    const today = new Date();
    const start = new Date(today.getFullYear(), 0, 1);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { projectId: 1, dateFrom: iso(start), dateTo: iso(today) };
  });
  const [data, setData] = useState<any>(null);

  async function load(v: FiltersValue) {
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&scenario=plan`;
    const r = await apiFetch(`/reports/cashflow${q}`);
    setData(r);
  }
  useEffect(()=>{ load(filters); }, []);

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
