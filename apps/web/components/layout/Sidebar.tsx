"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Database,
  BookOpen,
  HelpCircle,
  FileText,
  Settings,
  Sun,
  Moon,
  Sparkles
} from "lucide-react";
import { DataPilotLogo } from "@/components/brand/DataPilotLogo";
import { useTheme } from "@/lib/theme";

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Data Sources", href: "/sources", icon: Database },
  { name: "Business Knowledge", href: "/knowledge", icon: BookOpen },
  { name: "Ask Data", href: "/ask", icon: HelpCircle },
  { name: "Reports & Dashboards", href: "/reports", icon: FileText },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="w-64 border-r border-[var(--border-color)] bg-[var(--bg-surface)] flex flex-col h-screen sticky top-0 z-40 select-none transition-colors">
      {/* Brand Header with New Original SVG Logo */}
      <div className="h-14 flex items-center px-5 border-b border-[var(--border-color)]">
        <Link href="/" className="flex items-center gap-2">
          <DataPilotLogo size="sm" />
        </Link>
      </div>

      {/* Navigation Items (Only 5 active MVP modules) */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold tracking-wider text-[var(--text-muted)] uppercase">
          Workspace
        </div>
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-[var(--accent-teal-subtle)] text-[var(--accent-teal-text)] font-semibold border-l-2 border-[var(--accent-teal)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-subtle)]"
              }`}
            >
              <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-[var(--accent-teal)]" : "text-[var(--text-muted)]"}`} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>

      {/* Footer / Workspace & Theme Switcher */}
      <div className="p-3 border-t border-[var(--border-color)] bg-[var(--bg-surface-subtle)]">
        <div className="flex items-center justify-between p-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)]">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="h-6 w-6 rounded bg-[var(--accent-teal-subtle)] text-[var(--accent-teal)] flex items-center justify-center text-[10px] font-bold shrink-0">
              DP
            </div>
            <div className="truncate">
              <div className="text-[11px] font-semibold text-[var(--text-primary)] truncate">Primary Workspace</div>
              <div className="text-[10px] text-[var(--text-muted)]">Verified Engine</div>
            </div>
          </div>
          <button
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {theme === "light" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5 text-amber-400" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
