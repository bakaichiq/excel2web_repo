"use client";
import { useEffect, useState } from "react";
import Shell from "../../components/Shell";
import Filters, { FiltersValue } from "../../components/Filters";
import PercentChart from "../../components/PercentChart";
import { apiFetch, getProjectPlanRange } from "../../lib/api";

export default function Dashboard() {
  const [filters, setFilters] = useState<FiltersValue>(() => {
    return { projectId: 1, dateFrom: "", dateTo: "", wbsPath: "" };
  });
  const [floors, setFloors] = useState<any[]>([]);
  const [selectedFloor, setSelectedFloor] = useState<string | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null);
  const [floorSeries, setFloorSeries] = useState<any>(null);
  const [floorOps, setFloorOps] = useState<any[]>([]);
  const [loadingFloor, setLoadingFloor] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(v: FiltersValue) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}${wbs}`;
    try {
      setError(null);
      const summary = await apiFetch(`/reports/floors/summary${q}`);
      const rows = Array.isArray(summary?.rows) ? summary.rows : [];
      rows.sort((a: any, b: any) => {
        const ba = String(a.block ?? "");
        const bb = String(b.block ?? "");
        if (ba !== bb) return ba.localeCompare(bb);
        const na = parseFloat(String(a.floor).replace(",", "."));
        const nb = parseFloat(String(b.floor).replace(",", "."));
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return nb - na;
        return String(a.floor).localeCompare(String(b.floor));
      });
      setFloors(rows);
      const nextRow =
        rows.find((r: any) => r.floor === selectedFloor && r.block === selectedBlock) ||
        rows.find((r: any) => r.block === selectedBlock) ||
        rows[0] ||
        null;
      const nextFloor = nextRow?.floor || null;
      const nextBlock = nextRow?.block ?? null;
      setSelectedFloor(nextFloor);
      setSelectedBlock(nextBlock);
      if (nextFloor) {
        await loadFloor(nextFloor, nextBlock, v);
      } else {
        setFloorSeries(null);
        setFloorOps([]);
      }
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки этажей");
    }
  }

  async function loadFloor(floor: string, block: string | null, v: FiltersValue = filters) {
    const wbs = v.wbsPath ? `&wbs_path=${encodeURIComponent(v.wbsPath)}` : "";
    const blockParam = block ? `&block=${encodeURIComponent(block)}` : "";
    const q = `?project_id=${v.projectId}&date_from=${v.dateFrom}&date_to=${v.dateTo}${wbs}&floor=${encodeURIComponent(floor)}${blockParam}`;
    setLoadingFloor(true);
    try {
      const s = await apiFetch(`/reports/floors/series${q}`);
      const o = await apiFetch(`/reports/floors/operations${q}`);
      setFloorSeries(s);
      setFloorOps(Array.isArray(o?.rows) ? o.rows : []);
    } catch (e: any) {
      setError(e?.message || "Ошибка загрузки этажа");
    } finally {
      setLoadingFloor(false);
    }
  }

  useEffect(() => {
    let ignore = false;
    async function init() {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
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
        // fall back to current defaults
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

  const labelBlock = (val: string | null) => {
    if (!val) return "—";
    return String(val).replace(/^блок\s+/i, "").trim();
  };

  return (
    <Shell title="Excel2Web">
      <Filters initial={filters} onChange={(v)=>{ setFilters(v); load(v); }} />
      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
      {(() => {
        const selectedRow = floors.find((f: any) => f.floor === selectedFloor && f.block === selectedBlock);
        return (
      <div className="mt-4 flex flex-col md:flex-row gap-4">
        <div className="md:w-1/2">
          <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-4">
            <div className="text-sm text-neutral-400 mb-3">Здание</div>
            <div className="rounded-xl bg-gradient-to-b from-neutral-800/60 to-neutral-950/80 border border-neutral-800 p-3">
              {floors.length === 0 && <div className="text-sm text-neutral-500">Нет этажей.</div>}
              {(() => {
                const blocks = Array.from(
                  floors.reduce((acc: Map<string, any[]>, row: any) => {
                    const key = row.block ?? "Без блока";
                    acc.set(key, [...(acc.get(key) || []), row]);
                    return acc;
                  }, new Map())
                );
                    const blockNames = blocks.map(([b]) => b);
                const activeBlock = selectedBlock ?? blockNames[0] ?? null;
                const activeFloors = blocks.find(([b]) => b === activeBlock)?.[1] || [];
                return (
                  <>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {blockNames.map((b) => (
                        <button
                          key={b}
                          onClick={() => {
                            setSelectedBlock(b === "Без блока" ? null : b);
                            const floorRow = (blocks.find(([k]) => k === b)?.[1] || [])[0];
                            if (floorRow) {
                              setSelectedFloor(floorRow.floor);
                              loadFloor(floorRow.floor, floorRow.block ?? null);
                            } else {
                              setSelectedFloor(null);
                              setFloorOps([]);
                              setFloorSeries(null);
                            }
                          }}
                          className={`px-3 py-1 rounded-full text-xs border transition ${
                            (activeBlock || "Без блока") === b
                              ? "bg-emerald-500/15 border-emerald-400/50 text-emerald-200"
                              : "bg-neutral-900/60 border-neutral-800 text-neutral-300 hover:border-neutral-600"
                          }`}
                        >
                          {labelBlock(b === "Без блока" ? "" : b)}
                        </button>
                      ))}
                    </div>
                    <div className="flex flex-col gap-2">
                      {(activeFloors as any[]).map((f: any) => {
                        const isActive = selectedFloor === f.floor && selectedBlock === f.block;
                        const pct = Number(f.progress_pct || 0);
                        return (
                          <button
                            key={`${f.block ?? "Без блока"}-${f.floor}`}
                            onClick={() => {
                              setSelectedFloor(f.floor);
                              setSelectedBlock(f.block ?? null);
                              loadFloor(f.floor, f.block ?? null);
                            }}
                            className={`relative group rounded-lg border px-3 py-2 text-left transition ${
                              isActive ? "bg-emerald-500/10 border-emerald-400/40" : "bg-neutral-900/60 border-neutral-800 hover:border-neutral-600"
                            }`}
                          >
                            <div className="absolute inset-0 rounded-lg overflow-hidden">
                              <div
                                className="h-full bg-emerald-500/20"
                                style={{ width: `${Math.min(100, Math.max(0, pct)).toFixed(1)}%` }}
                              />
                            </div>
                            <div className="relative flex items-center justify-between">
                              <div className="text-sm font-semibold text-neutral-100">Этаж {f.floor}</div>
                              <div className="text-xs text-neutral-300">{pct.toFixed(1)}%</div>
                            </div>
                            <div className="relative text-[11px] text-neutral-500 mt-1">Операций: {f.operations_count}</div>
                          </button>
                        );
                      })}
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        </div>

        <div className="md:w-1/2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
              <div className="text-xs text-neutral-400">Секция</div>
              <div className="text-xl font-semibold mt-1">{labelBlock(selectedBlock)}</div>
            </div>
            <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
              <div className="text-xs text-neutral-400">Этаж</div>
              <div className="text-xl font-semibold mt-1">{selectedFloor || "—"}</div>
            </div>
            <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-4">
              <div className="text-xs text-neutral-400">Прогресс</div>
              <div className="text-xl font-semibold mt-1">
                {(selectedRow?.progress_pct || 0).toFixed(1)}%
              </div>
            </div>
          </div>

          <PercentChart title="Динамика выполнения по этажу" series={floorSeries} />

          <div className="mt-4 rounded-xl bg-neutral-900 border border-neutral-800 overflow-hidden">
            <div className="px-3 py-2 text-sm text-neutral-300 border-b border-neutral-800">
              Перечень работ
              <span className="text-xs text-neutral-500 ml-2">({selectedRow?.operations_count || 0})</span>
            </div>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-neutral-950/60 text-neutral-400">
                  <tr>
                    <th className="text-left px-3 py-2">Работа</th>
                    <th className="text-right px-3 py-2">%</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingFloor && (
                    <tr>
                      <td className="px-3 py-3 text-neutral-500" colSpan={2}>
                        Загрузка...
                      </td>
                    </tr>
                  )}
                  {!loadingFloor &&
                    floorOps.map((op: any) => (
                      <tr key={op.operation_code} className="border-t border-neutral-800">
                        <td className="px-3 py-2">
                          <div className="text-neutral-200">{op.operation_name}</div>
                          <div className="text-xs text-neutral-500">{op.operation_code}</div>
                        </td>
                        <td className="px-3 py-2 text-right">{Number(op.progress_pct || 0).toFixed(1)}%</td>
                      </tr>
                    ))}
                  {!loadingFloor && floorOps.length === 0 && (
                    <tr>
                      <td className="px-3 py-3 text-neutral-500" colSpan={2}>
                        Нет операций для выбранного этажа.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
        );
      })()}
    </Shell>
  );
}
