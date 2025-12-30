"use client";
import ReactECharts from "echarts-for-react";

type Point = { period: string; value: number };

export default function PercentChart({
  title,
  series,
}: {
  title: string;
  series: { plan?: Point[]; fact?: Point[]; forecast?: Point[] } | null;
}) {
  const planPoints = Array.isArray(series?.plan) ? [...(series?.plan || [])] : [];
  const factPoints = Array.isArray(series?.fact) ? [...(series?.fact || [])] : [];
  const forecastPoints = Array.isArray(series?.forecast) ? [...(series?.forecast || [])] : [];

  const planMap = new Map(planPoints.map((p) => [String(p.period).slice(0, 10), Number(p.value ?? 0)]));
  const factMap = new Map(factPoints.map((p) => [String(p.period).slice(0, 10), Number(p.value ?? 0)]));
  const forecastMap = new Map(forecastPoints.map((p) => [String(p.period).slice(0, 10), Number(p.value ?? 0)]));
  const periods = Array.from(new Set([...planMap.keys(), ...factMap.keys(), ...forecastMap.keys()])).sort();

  const planValues = periods.map((k) => planMap.get(k) ?? 0);
  const factValues = periods.map((k) => factMap.get(k) ?? 0);
  const forecastValues = periods.map((k) => forecastMap.get(k) ?? 0);
  const maxVal = Math.max(100, ...factValues, ...forecastValues);
  const yMax = Math.min(200, Math.ceil((maxVal + 10) / 10) * 10);
  const hasForecast = forecastMap.size > 0;

  const option = {
    title: { text: title, left: "left", textStyle: { color: "#e5e5e5", fontSize: 14 } },
    tooltip: { trigger: "axis", valueFormatter: (v: number) => `${v.toFixed(1)}%` },
    legend: { data: hasForecast ? ["plan", "fact", "forecast"] : ["plan", "fact"], top: 28, textStyle: { color: "#e5e5e5" } },
    grid: { left: 64, right: 20, top: 70, bottom: 30 },
    xAxis: { type: "category", data: periods, axisLabel: { color: "#a3a3a3" } },
    yAxis: {
      type: "value",
      min: 0,
      max: yMax,
      axisLabel: {
        color: "#a3a3a3",
        margin: 12,
        formatter: (v: number) => `${Number(v).toFixed(0)}%`,
      },
    },
    series: [
      { name: "plan", type: "line", data: planValues, smooth: true, lineStyle: { type: "dashed" } },
      { name: "fact", type: "line", data: factValues, smooth: true },
      ...(hasForecast ? [{ name: "forecast", type: "line", data: forecastValues, smooth: true }] : []),
    ],
  };

  return (
    <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-3 mt-4">
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
