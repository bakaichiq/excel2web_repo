"use client";
import ReactECharts from "echarts-for-react";

export default function LineChart({ title, series }: { title: string; series: any }) {
  const planPoints = Array.isArray(series?.plan) ? [...series.plan] : [];
  const factPoints = Array.isArray(series?.fact) ? [...series.fact] : [];
  const forecastPoints = Array.isArray(series?.forecast) ? [...series.forecast] : [];

  const planMap = new Map<string, number>();
  const factMap = new Map<string, number>();
  const forecastMap = new Map<string, number>();

  for (const p of planPoints) {
    planMap.set(String(p.period).slice(0, 10), Number(p.value ?? 0));
  }
  for (const p of factPoints) {
    factMap.set(String(p.period).slice(0, 10), Number(p.value ?? 0));
  }
  for (const p of forecastPoints) {
    forecastMap.set(String(p.period).slice(0, 10), Number(p.value ?? 0));
  }

  const periods = Array.from(new Set([...planMap.keys(), ...factMap.keys(), ...forecastMap.keys()])).sort();
  const planValues = periods.map((k) => planMap.get(k) ?? 0);
  const factValues = periods.map((k) => factMap.get(k) ?? 0);
  const forecastValues = periods.map((k) => forecastMap.get(k) ?? 0);
  const hasForecast = forecastMap.size > 0;

  const option = {
    title: { text: title, left: "left", textStyle: { color: "#e5e5e5", fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { data: hasForecast ? ["plan", "fact", "forecast"] : ["plan", "fact"], top: 28, textStyle: { color: "#e5e5e5" } },
    grid: { left: 64, right: 20, top: 70, bottom: 30 },
    xAxis: { type: "category", data: periods, axisLabel: { color: "#a3a3a3" } },
    yAxis: {
      type: "value",
      min: 0,
      axisLabel: {
        color: "#a3a3a3",
        margin: 12,
        formatter: (v: number) => Number(v).toLocaleString("ru-RU"),
      },
    },
    series: [
      { name: "plan", type: "bar", data: planValues, barWidth: 18 },
      { name: "fact", type: "bar", data: factValues, barWidth: 18 },
      ...(hasForecast
        ? [{ name: "forecast", type: "line", smooth: true, data: forecastValues }]
        : []),
    ]
  };
  return (
    <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-3 mt-4">
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
