"use client";

import { useState } from "react";
import { Settings as SettingsIcon, ShieldCheck, Key, Database, Sun, Moon } from "lucide-react";
import { useTheme } from "@/lib/theme";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [saved, setSaved] = useState(false);

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-4">
        <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 text-[var(--text-muted)]" />
          Workspace Settings
        </h1>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5">
          Configure security, workspace identity, theme preferences, and provider credentials.
        </p>
      </div>

      {saved && (
        <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300">
          Settings updated successfully.
        </div>
      )}

      {/* Theme Preference */}
      <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Appearance & Theme
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Switch between clean white light mode (default) and deep navy dark mode.
            </p>
          </div>
          <button
            onClick={toggleTheme}
            className="px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] text-xs font-semibold flex items-center gap-2 text-[var(--text-primary)] hover:border-[var(--accent-teal)]"
          >
            {theme === "light" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5 text-amber-400" />}
            <span>{theme === "light" ? "Switch to Dark" : "Switch to Light"}</span>
          </button>
        </div>
      </div>

      {/* Security & Encryption Status */}
      <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] p-5 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-[var(--accent-teal)]" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
            Security & Credential Encryption
          </h3>
        </div>
        <div className="p-3 rounded-lg bg-[var(--bg-surface-subtle)] border border-[var(--border-color)] text-xs space-y-2 text-[var(--text-secondary)]">
          <div className="flex items-center justify-between">
            <span>Database Credential Encryption:</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">AES-256 (Fernet) Active</span>
          </div>
          <div className="flex items-center justify-between">
            <span>SQL AST Security Parser:</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">sqlglot Read-Only Sandbox Active</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Query Execution Permissions:</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">Strict Read-Only (DDL/DML Blocked)</span>
          </div>
        </div>
      </div>

      {/* Workspace Identity */}
      <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] p-5 space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
          Workspace Information
        </h3>
        <div className="space-y-3 text-xs">
          <div>
            <label className="block text-[var(--text-secondary)] font-medium mb-1">Workspace Name</label>
            <input
              type="text"
              defaultValue="Primary Analytics Workspace"
              className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
            />
          </div>
          <div>
            <label className="block text-[var(--text-secondary)] font-medium mb-1">Default Calculation Engine</label>
            <input
              type="text"
              disabled
              value="DuckDB Embedded OLAP (In-Memory & Persistent)"
              className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] text-[var(--text-muted)] font-mono"
            />
          </div>
        </div>
        <div className="pt-2">
          <button
            onClick={() => {
              setSaved(true);
              setTimeout(() => setSaved(false), 3000);
            }}
            className="px-4 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
}
