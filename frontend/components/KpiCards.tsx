"use client";
export default function KpiCards({ kpi }: { kpi: any }) {
  const fmt1 = (v: any) => (typeof v === "number" ? v.toFixed(1) : v ?? "—");
  const items = [
    { label: "Факт", value: fmt1(kpi?.fact_qty) },
    { label: "План", value: fmt1(kpi?.plan_qty) },
    { label: "Прогресс %", value: kpi ? kpi.progress_pct.toFixed(2) : "—" },
    { label: "Manhours", value: kpi?.manhours ?? "—" },
    { label: "Производительность", value: kpi?.productivity ?? "—" }
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mt-4">
      {items.map((it) => (
        <div key={it.label} className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
          <div className="text-xs text-neutral-400">{it.label}</div>
          <div className="text-xl font-semibold mt-1">{it.value}</div>
        </div>
      ))}
    </div>
  );
}
