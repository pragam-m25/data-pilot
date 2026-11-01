"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Database,
  BookOpen,
  HelpCircle,
  FileText,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Plus
} from "lucide-react";
import { fetchApi } from "@/lib/api";

export default function OverviewPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [recentQueries, setRecentQueries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const [sData, mData, rData, qData] = await Promise.allSettled([
          fetchApi("/api/v1/sources"),
          fetchApi("/api/v1/knowledge/metrics"),
          fetchApi("/api/v1/reports"),
          fetchApi("/api/v1/query/history?limit=5"),
        ]);

        if (sData.status === "fulfilled" && Array.isArray(sData.value)) {
          setSources(sData.value);
        }
        if (mData.status === "fulfilled" && Array.isArray(mData.value)) {
          setMetrics(mData.value);
        }
        if (rData.status === "fulfilled" && Array.isArray(rData.value)) {
          setReports(rData.value);
        }
        if (qData.status === "fulfilled" && Array.isArray(qData.value)) {
          setRecentQueries(qData.value);
        }
      } catch (err) {
        console.error("Failed to load overview data", err);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="border-b border-[var(--border-color)] pb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            Workspace Overview
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            DataPilot delivers verifiable business analytics based on your company's actual operational data and approved metric formulas.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/sources"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Upload Dataset</span>
          </Link>
          <Link
            href="/knowledge"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)] text-[var(--text-primary)] text-xs font-medium transition-all"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Define Metric</span>
          </Link>
        </div>
      </div>

      {/* Trust & Verification Banner */}
      <div className="p-3.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-[var(--accent-teal)] shrink-0 mt-0.5" />
        <div className="text-xs">
          <span className="font-semibold text-[var(--text-primary)]">Verifiable Calculations Active: </span>
          <span className="text-[var(--text-secondary)]">
            Every query executed is strictly read-only, validated via AST parser, and mapped to an approved metric definition. Zero synthetic or guessed metrics.
          </span>
        </div>
      </div>

      {/* 4 Core Pillars Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
            <span>Data Sources</span>
            <Database className="h-4 w-4 text-[var(--accent-teal)]" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {sources.length}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] mt-1">
            {sources.length > 0 ? "Real CSV/XLSX & PostgreSQL" : "No sources added yet"}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
            <span>Approved Metrics</span>
            <BookOpen className="h-4 w-4 text-[var(--accent-teal)]" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {metrics.filter(m => m.status === "approved").length}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] mt-1">
            {metrics.length > 0 ? `${metrics.length} total metric versions` : "Awaiting business definitions"}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
            <span>Verified Queries</span>
            <HelpCircle className="h-4 w-4 text-[var(--accent-teal)]" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {recentQueries.length}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] mt-1">
            Executed with complete calculation trace
          </p>
        </div>

        <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
            <span>Saved Reports</span>
            <FileText className="h-4 w-4 text-[var(--accent-teal)]" />
          </div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">
            {reports.length}
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] mt-1">
            Backed strictly by validated results
          </p>
        </div>
      </div>

      {/* Main Grid: Data Sources & Recent Traceable Calculations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Active Data Sources */}
        <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between bg-[var(--bg-surface-subtle)]">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
              Connected Data Sources
            </h3>
            <Link href="/sources" className="text-xs text-[var(--accent-teal)] hover:underline">
              View all
            </Link>
          </div>
          {sources.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <Database className="h-8 w-8 text-[var(--text-muted)] mx-auto opacity-50" />
              <p className="text-xs text-[var(--text-secondary)]">No data sources connected yet.</p>
              <Link
                href="/sources"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-teal)] text-white text-xs font-medium"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Upload CSV or Connect PostgreSQL</span>
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border-color)]">
              {sources.slice(0, 5).map((src) => (
                <div key={src.id} className="p-3.5 flex items-center justify-between hover:bg-[var(--bg-surface-subtle)] transition-colors">
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-primary)]">{src.name}</p>
                    <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
                      {src.row_count?.toLocaleString()} rows · {src.column_count} columns · {src.file_type?.toUpperCase()}
                    </p>
                  </div>
                  <Link
                    href={`/sources`}
                    className="text-xs text-[var(--accent-teal)] hover:underline font-medium"
                  >
                    Inspect Profile →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Recent Query Calculations */}
        <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between bg-[var(--bg-surface-subtle)]">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
              Recent Calculations & Audits
            </h3>
            <Link href="/ask" className="text-xs text-[var(--accent-teal)] hover:underline">
              Ask question
            </Link>
          </div>
          {recentQueries.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <HelpCircle className="h-8 w-8 text-[var(--text-muted)] mx-auto opacity-50" />
              <p className="text-xs text-[var(--text-secondary)]">No queries executed yet.</p>
              <p className="text-[11px] text-[var(--text-muted)] max-w-xs mx-auto">
                Ask a natural-language question resolved against your approved business formulas.
              </p>
              <Link
                href="/ask"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[var(--border-color)] text-[var(--text-primary)] text-xs font-medium hover:bg-[var(--bg-surface-subtle)]"
              >
                <span>Go to Ask Data</span>
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border-color)]">
              {recentQueries.map((q) => (
                <div key={q.id} className="p-3.5 hover:bg-[var(--bg-surface-subtle)] transition-colors">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium text-[var(--text-primary)] truncate max-w-sm">
                      "{q.question}"
                    </p>
                    <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                      {q.execution_ms}ms · {q.row_count} rows
                    </span>
                  </div>
                  <pre className="mt-1.5 p-1.5 rounded bg-[var(--bg-surface-subtle)] text-[10px] font-mono text-[var(--text-secondary)] overflow-x-auto truncate">
                    {q.sql}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
