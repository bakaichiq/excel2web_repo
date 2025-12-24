"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import { apiFetch } from "../../../lib/api";

export default function PnlPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    const today = new Date();
    const start = new Date(today.getFullYear(), 0, 1);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { projectId: 1, dateFrom: iso(start), dateTo: iso(today) };
  });
  const [rows, setRows] = useState<any[]>([]);

  async function load(v: FiltersValue) {
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&scenario=plan`;
    const r = await apiFetch(`/reports/pnl${q}`);
    setRows(r);
  }
  useEffect(()=>{ load(filters); }, []);
  return (
    <Shell title="БДР (P&L)">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">Месяц</th>
              <th className="text-left px-3 py-2">Статья</th>
              <th className="text-right px-3 py-2">Сумма</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0,200).map((r:any,i)=>(
              <tr key={i} className="border-t border-neutral-800">
                <td className="px-3 py-2">{String(r.month).slice(0,10)}</td>
                <td className="px-3 py-2">{r.account}</td>
                <td className="px-3 py-2 text-right">{Number(r.amount).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
