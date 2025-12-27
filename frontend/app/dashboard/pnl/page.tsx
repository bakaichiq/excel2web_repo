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
  const [scenario, setScenario] = useState<"plan" | "fact">("plan");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [expandAll, setExpandAll] = useState(true);
  const [totalMode, setTotalMode] = useState<"leaf" | "all">("leaf");

  async function load(v: FiltersValue, sc = scenario) {
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}&scenario=${sc}`;
    const r = await apiFetch(`/reports/pnl${q}`);
    setRows(r);
  }
  useEffect(()=>{ load(filters); }, []);

  const months = Array.from(new Set(rows.map((r) => String(r.month).slice(0, 7)))).sort();
  const byAccount: Record<string, Record<string, number>> = {};
  const parentByAccount: Record<string, string | null> = {};
  rows.forEach((r) => {
    const acc = r.account || "—";
    const m = String(r.month).slice(0, 7);
    if (!byAccount[acc]) byAccount[acc] = {};
    byAccount[acc][m] = (byAccount[acc][m] || 0) + Number(r.amount || 0);
    parentByAccount[acc] = r.parent_name || null;
  });

  const totalsByMonthAll: Record<string, number> = {};
  rows.forEach((r) => {
    const m = String(r.month).slice(0, 7);
    totalsByMonthAll[m] = (totalsByMonthAll[m] || 0) + Number(r.amount || 0);
  });

  type Node = {
    name: string;
    parent: string | null;
    values: Record<string, number>;
    children: Node[];
  };

  const nodeMap: Record<string, Node> = {};
  Object.keys(byAccount).forEach((name) => {
    nodeMap[name] = {
      name,
      parent: parentByAccount[name] || null,
      values: { ...byAccount[name] },
      children: [],
    };
  });
  Object.values(nodeMap).forEach((node) => {
    if (node.parent && nodeMap[node.parent]) {
      nodeMap[node.parent].children.push(node);
    }
  });

  function aggregate(node: Node, mode: "leaf" | "all"): Record<string, number> {
    const agg = mode === "all" ? { ...node.values } : {};
    node.children.forEach((child) => {
      const c = aggregate(child, mode);
      Object.keys(c).forEach((m) => {
        agg[m] = (agg[m] || 0) + c[m];
      });
    });
    if (mode === "leaf" && node.children.length === 0) {
      Object.keys(node.values).forEach((m) => {
        agg[m] = (agg[m] || 0) + node.values[m];
      });
    }
    node.values = agg;
    return agg;
  }

  Object.values(nodeMap).forEach((node) => {
    if (!node.parent) aggregate(node, totalMode);
  });

  function flatten(nodes: Node[], depth = 0): Array<{ node: Node; depth: number }> {
    const out: Array<{ node: Node; depth: number }> = [];
    nodes
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((n) => {
        out.push({ node: n, depth });
        if (n.children.length) {
          out.push(...flatten(n.children, depth + 1));
        }
      });
    return out;
  }

  const treeRows = flatten(Object.values(nodeMap).filter((n) => !n.parent));
  const totalsByMonth =
    totalMode === "all"
      ? totalsByMonthAll
      : months.reduce<Record<string, number>>((acc, m) => {
          acc[m] = treeRows
            .filter((r) => r.node.children.length === 0)
            .reduce((s, r) => s + (r.node.values[m] || 0), 0);
          return acc;
        }, {});
  const totalRowSum = months.reduce((acc, m) => acc + (totalsByMonth[m] || 0), 0);

  function isVisible(node: Node): boolean {
    if (expandAll) return true;
    let parent = node.parent ? nodeMap[node.parent] : null;
    while (parent) {
      if (!expanded[parent.name]) return false;
      parent = parent.parent ? nodeMap[parent.parent] : null;
    }
    return true;
  }
  return (
    <Shell title="БДР (P&L)">
      <div className="flex flex-wrap gap-4 items-end">
        <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
        <div className="flex items-end gap-2">
          <button
            className="px-3 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm"
            onClick={() => {
              setExpandAll(true);
              setExpanded({});
            }}
          >
            Развернуть всё
          </button>
          <button
            className="px-3 py-2 rounded bg-neutral-800 hover:bg-neutral-700 text-sm"
            onClick={() => {
              setExpandAll(false);
              setExpanded({});
            }}
          >
            Свернуть всё
          </button>
        </div>
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Развёртка</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={expandAll ? "all" : "custom"}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "all") {
                setExpandAll(true);
              } else {
                setExpandAll(false);
              }
            }}
          >
            <option value="all">Все уровни</option>
            <option value="custom">Выборочно</option>
          </select>
        </label>
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Итоги</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={totalMode}
            onChange={(e) => setTotalMode(e.target.value as "leaf" | "all")}
          >
            <option value="leaf">Только по листьям</option>
            <option value="all">Включая родителей</option>
          </select>
        </label>
        <label className="text-sm">
          <div className="text-neutral-400 mb-1">Сценарий</div>
          <select
            className="px-3 py-2 rounded bg-neutral-900 border border-neutral-800"
            value={scenario}
            onChange={(e) => {
              const sc = e.target.value as "plan" | "fact";
              setScenario(sc);
              load(filters, sc);
            }}
          >
            <option value="plan">План</option>
            <option value="fact">Факт</option>
          </select>
        </label>
      </div>
      <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-950/60 text-neutral-300">
            <tr>
              <th className="text-left px-3 py-2">Статья</th>
              {months.map((m) => (
                <th key={m} className="text-right px-3 py-2">{m}</th>
              ))}
              <th className="text-right px-3 py-2">Итого</th>
            </tr>
          </thead>
          <tbody>
            {treeRows.slice(0, 500).map(({ node, depth }) => {
              const isExpanded = expandAll || expanded[node.name] || false;
              const isLeaf = node.children.length === 0;
              if (!isVisible(node)) return null;
              const rowTotal = months.reduce((acc, m) => acc + (node.values[m] || 0), 0);
              return (
                <tr key={node.name} className="border-t border-neutral-800">
                  <td className="px-3 py-2">
                    <span style={{ paddingLeft: `${depth * 16}px` }} className="inline-flex items-center gap-2">
                      {!isLeaf && (
                        <button
                          className="text-neutral-400 hover:text-neutral-200"
                          onClick={() =>
                            setExpanded((prev) => ({ ...prev, [node.name]: !prev[node.name] }))
                          }
                          title={isExpanded ? "Свернуть" : "Развернуть"}
                        >
                          {isExpanded ? "▾" : "▸"}
                        </button>
                      )}
                      {node.name}
                    </span>
                  </td>
                  {months.map((m) => (
                    <td key={`${node.name}-${m}`} className="px-3 py-2 text-right">
                      {Number(node.values[m] || 0).toFixed(2)}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-right">{rowTotal.toFixed(2)}</td>
                </tr>
              );
            })}
            {treeRows.length > 0 && (
              <tr className="border-t border-neutral-700 bg-neutral-950/60 text-neutral-200">
                <td className="px-3 py-2 font-semibold">Итого</td>
                {months.map((m) => (
                  <td key={`total-${m}`} className="px-3 py-2 text-right font-semibold">
                    {Number(totalsByMonth[m] || 0).toFixed(2)}
                  </td>
                ))}
                <td className="px-3 py-2 text-right font-semibold">{totalRowSum.toFixed(2)}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
