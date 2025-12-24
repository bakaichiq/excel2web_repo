"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { clearToken, apiFetch } from "../lib/api";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Главная", icon: "M3 12h18" },
  { href: "/dashboard/progress", label: "Прогресс", icon: "M4 18h16M6 14h12M8 10h8M10 6h4" },
  { href: "/dashboard/gpr", label: "ГПР", icon: "M4 6h16M4 12h10M4 18h7" },
  { href: "/dashboard/ugpr", label: "УГПР", icon: "M4 12h16M12 4v16M6 6l12 12" },
  { href: "/dashboard/pnl", label: "БДР", icon: "M4 17l5-5 4 4 7-7" },
  { href: "/dashboard/cashflow", label: "БДДС", icon: "M5 12h14M7 8h10M9 16h6" },
  { href: "/dashboard/manhours", label: "Manhours", icon: "M8 6h8M4 18h16M6 10h12" },
  { href: "/dashboard/import", label: "Импорт", icon: "M12 4v10M8 10l4 4 4-4M4 18h16" },
];

export default function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  const router = useRouter();
  const [userLabel, setUserLabel] = useState<string>("—");

  useEffect(() => {
    let ignore = false;
    async function loadUser() {
      try {
        const me = await apiFetch("/auth/me");
        if (ignore) return;
        setUserLabel(me?.full_name || me?.login || "—");
      } catch {
        if (!ignore) setUserLabel("—");
      }
    }
    loadUser();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 text-neutral-100">
      <div className="flex min-h-screen">
        <aside className="w-20 md:w-24 border-r border-neutral-800 bg-neutral-950/70 backdrop-blur flex flex-col items-center py-4 gap-4">
          <div className="w-10 h-10 rounded-2xl bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-sm font-semibold">
            IBM
          </div>
          <nav className="flex flex-col gap-3 text-xs text-neutral-300">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex flex-col items-center gap-1 px-2 py-2 rounded-lg hover:bg-neutral-800/60"
                title={item.label}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d={item.icon} />
                </svg>
                <span className="hidden md:block">{item.label}</span>
              </Link>
            ))}
          </nav>
          <div className="mt-auto text-[10px] text-neutral-500">v0.1</div>
        </aside>

        <div className="flex-1">
          <div className="border-b border-neutral-800 bg-neutral-950/60 backdrop-blur sticky top-0 z-10">
            <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
              <div className="font-semibold">{title}</div>
              <div className="flex items-center gap-3">
                <div className="text-sm text-neutral-300">{userLabel}</div>
                <button
                  className="text-sm px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700"
                  onClick={() => {
                    clearToken();
                    router.push("/login");
                  }}
                >
                  Выйти
                </button>
              </div>
            </div>
          </div>
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
