"use client";
import { useState } from "react";

export type FiltersValue = {
  projectId: number;
  dateFrom: string;
  dateTo: string;
  wbsPath?: string;
};

export default function Filters({ initial, onChange }: { initial: FiltersValue; onChange: (v: FiltersValue) => void }) {
  const [v, setV] = useState<FiltersValue>(initial);
  return (
    <div className="flex flex-wrap gap-3 items-end">
      <label className="text-sm">
        <div className="text-neutral-400 mb-1">Проект ID</div>
        <input
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800 w-32"
          type="number"
          value={v.projectId}
          onChange={(e) => setV({ ...v, projectId: parseInt(e.target.value || "1") })}
        />
      </label>
      <label className="text-sm">
        <div className="text-neutral-400 mb-1">С</div>
        <input
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          type="date"
          value={v.dateFrom}
          onChange={(e) => setV({ ...v, dateFrom: e.target.value })}
        />
      </label>
      <label className="text-sm">
        <div className="text-neutral-400 mb-1">По</div>
        <input
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          type="date"
          value={v.dateTo}
          onChange={(e) => setV({ ...v, dateTo: e.target.value })}
        />
      </label>
      <label className="text-sm">
        <div className="text-neutral-400 mb-1">WBS</div>
        <input
          className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
          value={v.wbsPath || ""}
          onChange={(e) => setV({ ...v, wbsPath: e.target.value })}
          placeholder="WBS путь"
        />
      </label>
      <button
        className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm"
        onClick={() => onChange(v)}
      >
        Применить
      </button>
    </div>
  );
}
