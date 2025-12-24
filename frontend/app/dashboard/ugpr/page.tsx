"use client";
import { useEffect, useState } from "react";
import Shell from "../../../components/Shell";
import Filters, { FiltersValue } from "../../../components/Filters";
import MoneyChart from "../../../components/MoneyChart";
import { apiFetch } from "../../../lib/api";

export default function UgprPage() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    const today = new Date();
    const start = new Date(today.getFullYear(), 0, 1);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return { projectId: 1, dateFrom: iso(start), dateTo: iso(today), wbsPath: "" };
  });
  const [series, setSeries] = useState<any>(null);
  const [granularity, setGranularity] = useState<"day" | "week" | "month">("month");
  const [error, setError] = useState<string | null>(null);

  async function load(v: FiltersValue = filters, g = granularity) {
    try {
      setError(null);
      const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
      const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&granularity=${g}${wbs}`;
      const r = await apiFetch(`/reports/ugpr/series${q}`);
      setSeries(r);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки УГПР");
    }
  }

  useEffect(() => {
    load(filters);
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
    </Shell>
  );
}
