"use client";

import { useState, useEffect } from "react";
import { Sun, Moon, Search, Command, CheckCircle2, AlertCircle } from "lucide-react";
import { useTheme } from "@/lib/theme";

export function TopNav() {
  const { theme, toggleTheme } = useTheme();
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then(r => r.ok ? setApiStatus("online") : setApiStatus("offline"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <header className="h-14 border-b border-[var(--border-color)] bg-[var(--bg-surface)] px-6 flex items-center justify-between sticky top-0 z-30 transition-colors">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span className="font-semibold text-[var(--text-primary)]">DataPilot</span>
          <span>/</span>
          <span className="text-[var(--text-secondary)] font-medium">Verified Analytics Workspace</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Real Backend Status Indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)]">
          {apiStatus === "online" ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              <span className="text-[11px]">API: Connected</span>
            </>
          ) : apiStatus === "checking" ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
              <span className="text-[11px]">API: Connecting...</span>
            </>
          ) : (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-red-400"></span>
              <span className="text-[11px]">API: Offline</span>
            </>
          )}
        </div>

        {/* Theme Toggle Button: Light (White) by default, Dark when toggled */}
        <button
          onClick={toggleTheme}
          aria-label={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          className="p-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all flex items-center gap-1.5 text-xs font-medium"
        >
          {theme === "light" ? (
            <>
              <Moon className="h-4 w-4 text-slate-600" />
              <span className="hidden sm:inline">Dark</span>
            </>
          ) : (
            <>
              <Sun className="h-4 w-4 text-amber-400" />
              <span className="hidden sm:inline">Light</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
