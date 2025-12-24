"use client";
import ReactECharts from "echarts-for-react";

export default function MoneyChart({
  title,
  series,
}: {
  title: string;
  series: { series?: { period: string; value: number }[]; plan?: { period: string; value: number }[] } | null;
}) {
  const points = Array.isArray(series?.series) ? [...(series?.series || [])] : [];
  const planPoints = Array.isArray(series?.plan) ? [...(series?.plan || [])] : [];
  points.sort((a, b) => String(a.period).localeCompare(String(b.period)));
  planPoints.sort((a, b) => String(a.period).localeCompare(String(b.period)));

  const dataMap = new Map(points.map((p) => [String(p.period).slice(0, 10), Number(p.value ?? 0)]));
  const planMap = new Map(planPoints.map((p) => [String(p.period).slice(0, 10), Number(p.value ?? 0)]));
  const periods = Array.from(new Set([...dataMap.keys(), ...planMap.keys()])).sort();
  const values = periods.map((p) => dataMap.get(p) ?? 0);
  const planValues = periods.map((p) => planMap.get(p) ?? 0);
  const hasPlan = planMap.size > 0;

  const option = {
    title: { text: title, left: "left", textStyle: { color: "#e5e5e5", fontSize: 14 } },
    tooltip: { trigger: "axis" },
    grid: { left: 120, right: 20, top: 70, bottom: 30 },
    xAxis: { type: "category", data: periods, axisLabel: { color: "#a3a3a3" } },
    yAxis: {
      type: "value",
      min: 0,
      axisLabel: {
        color: "#a3a3a3",
        margin: 16,
        align: "right",
        formatter: (v: number) => `${Number(v).toLocaleString("ru-RU")} сом`,
      },
    },
    series: [
      { name: "Освоено", type: "line", smooth: true, data: values },
      ...(hasPlan ? [{ name: "План", type: "line", smooth: true, data: planValues, lineStyle: { type: "dashed" } }] : []),
    ],
    legend: { data: hasPlan ? ["Освоено", "План"] : ["Освоено"], top: 28, textStyle: { color: "#e5e5e5" } },
  };

  return (
    <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-3 mt-4">
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
