"use client";

import { useState, useEffect } from "react";
import {
  HelpCircle,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Play,
  Table as TableIcon,
  Clock,
  ShieldCheck,
  FileCode,
  ArrowRight
} from "lucide-react";
import { fetchApi } from "@/lib/api";

export default function AskDataPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [question, setQuestion] = useState("");
  const [queryState, setQueryState] = useState<any | null>(null);
  const [executionResult, setExecutionResult] = useState<any | null>(null);
  const [asking, setAsking] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function loadInitial() {
    try {
      const [srcs, hist] = await Promise.all([
        fetchApi("/api/v1/sources"),
        fetchApi("/api/v1/query/history?limit=10"),
      ]);
      if (Array.isArray(srcs) && srcs.length > 0) {
        setSources(srcs);
        setSelectedSourceId(srcs[0].id);
      }
      if (Array.isArray(hist)) {
        setHistory(hist);
      }
    } catch (e: any) {
      console.error("Failed to load sources or history", e);
    }
  }

  useEffect(() => {
    loadInitial();
  }, []);

  async function handleAsk() {
    if (!question.trim() || !selectedSourceId) return;
    setAsking(true);
    setQueryState(null);
    setExecutionResult(null);
    setErrorMsg(null);

    try {
      const res = await fetchApi("/api/v1/query/ask", {
        method: "POST",
        body: JSON.stringify({
          question: question.trim(),
          source_id: selectedSourceId
        })
      });
      setQueryState(res);
    } catch (e: any) {
      setErrorMsg("Error resolving inquiry: " + e.message);
    } finally {
      setAsking(false);
    }
  }

  async function handleExecute() {
    if (!queryState?.query_id) return;
    setExecuting(true);
    setErrorMsg(null);
    try {
      const res = await fetchApi("/api/v1/query/execute", {
        method: "POST",
        body: JSON.stringify({
          query_id: queryState.query_id,
          confirmed: true
        })
      });
      setExecutionResult(res);
      // Reload history
      const hist = await fetchApi("/api/v1/query/history?limit=10");
      if (Array.isArray(hist)) setHistory(hist);
    } catch (e: any) {
      setErrorMsg("Execution error: " + e.message);
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-[var(--accent-teal)]" />
            Ask Data — Verifiable Analytical Inquiries
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Ask questions in plain English. Intent is matched against approved company metrics and executed as AST-validated read-only SQL.
          </p>
        </div>
      </div>

      {/* Query Bar */}
      <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="w-full sm:w-64">
            <label className="block text-[10px] font-bold uppercase text-[var(--text-muted)] mb-1">Target Source</label>
            <select
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)] font-medium"
            >
              {sources.length === 0 ? (
                <option value="">No sources found</option>
              ) : (
                sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.row_count?.toLocaleString()} rows)
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="flex-1">
            <label className="block text-[10px] font-bold uppercase text-[var(--text-muted)] mb-1">Business Question</label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. What is our net revenue by region?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                className="flex-1 px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)] placeholder:text-[var(--text-muted)]"
              />
              <button
                onClick={handleAsk}
                disabled={asking || !question.trim() || !selectedSourceId}
                className="px-4 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              >
                {asking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                <span>Resolve</span>
              </button>
            </div>
          </div>
        </div>

        {/* Suggestion Prompts */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-[var(--text-muted)]">
          <span>Try:</span>
          {[
            "What is our net revenue by region?",
            "What is the average order amount?",
            "Total orders by status"
          ].map((sample) => (
            <button
              key={sample}
              onClick={() => {
                setQuestion(sample);
              }}
              className="px-2 py-0.5 rounded border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              "{sample}"
            </button>
          ))}
        </div>
      </div>

      {/* Inline Execution / Query Error Notice */}
      {errorMsg && (
        <div className="p-4 rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-xs space-y-1.5 animate-in fade-in">
          <div className="flex items-center justify-between font-bold text-rose-800 dark:text-rose-300">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
              <span>Query Execution Notice</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-[10px] uppercase tracking-wider text-rose-600 dark:text-rose-400 hover:underline font-bold"
            >
              Dismiss
            </button>
          </div>
          <p className="text-rose-900 dark:text-rose-200 font-mono text-[11px] leading-relaxed break-words">
            {errorMsg}
          </p>
        </div>
      )}

      {/* Query Resolution State */}
      {queryState && (
        <div className="space-y-4">
          {/* Case 0: Schema / SQL Validation Error */}
          {queryState.status === "validation_error" && (
            <div className="p-4 rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 space-y-2 text-xs">
              <div className="flex items-center gap-2 text-rose-800 dark:text-rose-300 font-bold">
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                <span>Schema Validation Notice</span>
              </div>
              <p className="text-rose-900 dark:text-rose-200 leading-relaxed font-mono">
                {queryState.message}
              </p>
              {queryState.raw_sql && (
                <pre className="p-2 rounded bg-rose-100/50 dark:bg-rose-900/30 text-[10px] text-rose-900 dark:text-rose-200 overflow-x-auto whitespace-pre-wrap">
                  {queryState.raw_sql}
                </pre>
              )}
            </div>
          )}

          {/* Case 1: Missing Metric Definition */}
          {queryState.status === "needs_definition" && (
            <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 space-y-2 text-xs">
              <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold">
                <AlertTriangle className="h-4 w-4" />
                <span>Approved Metric Missing</span>
              </div>
              <p className="text-amber-900 dark:text-amber-200 leading-relaxed">
                {queryState.message}
              </p>
              <div className="pt-2">
                <a
                  href="/knowledge"
                  className="inline-flex items-center gap-1 font-semibold text-[var(--accent-teal-text)] hover:underline"
                >
                  <span>Go to Business Knowledge to define this metric</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* Case 2: Ambiguous Clarification Required */}
          {queryState.status === "needs_clarification" && (
            <div className="p-4 rounded-xl border border-blue-300 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 space-y-3 text-xs">
              <div className="flex items-center gap-2 text-blue-800 dark:text-blue-300 font-bold">
                <HelpCircle className="h-4 w-4" />
                <span>Clarification Required</span>
              </div>
              <p className="text-blue-900 dark:text-blue-200">
                {queryState.message}
              </p>
              <div className="space-y-1.5">
                {queryState.candidates?.map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setQuestion(`What is ${c.name}?`);
                    }}
                    className="w-full text-left p-2 rounded border border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-900 text-xs text-[var(--text-primary)] hover:border-[var(--accent-teal)] transition-colors flex items-center justify-between"
                  >
                    <span className="font-semibold">{c.name} (v{c.version})</span>
                    <span className="font-mono text-[10px] text-[var(--text-muted)]">{c.formula}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Case 3: Ready to Execute (AST Validated SQL) */}
          {queryState.status === "ready_to_execute" && (
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden space-y-4 p-4">
              <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-xs font-bold text-[var(--text-primary)]">
                    Resolved to Metric: {queryState.metric_name} (v{queryState.metric_version})
                  </span>
                </div>
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="px-4 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {executing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  <span>Execute Validated SQL</span>
                </button>
              </div>

              <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
                <span className="font-semibold text-[var(--text-primary)]">Calculation Plan: </span>
                {queryState.explanation}
              </div>

              {/* Verified SQL AST Preview */}
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] p-3">
                <div className="flex items-center justify-between text-[10px] font-bold uppercase text-[var(--text-muted)] mb-1.5">
                  <span className="flex items-center gap-1">
                    <FileCode className="h-3.5 w-3.5" /> Generated Read-Only SQL (AST Verified)
                  </span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-mono">SELECT only · LIMIT 50</span>
                </div>
                <pre className="text-xs font-mono text-[var(--text-primary)] overflow-x-auto whitespace-pre-wrap">
                  {queryState.sql}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Execution Results & Verified Lineage */}
      {executionResult && (
        <div className="space-y-4">
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
            <div className="px-4 py-3 border-b border-[var(--border-color)] bg-[var(--bg-surface-subtle)] flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2">
                <TableIcon className="h-4 w-4 text-[var(--accent-teal)]" />
                Query Execution Results ({executionResult.row_count} rows in {executionResult.execution_ms}ms)
              </span>
            </div>

            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border-b border-[var(--border-color)] sticky top-0">
                  <tr>
                    {executionResult.columns.map((c: string) => (
                      <th key={c} className="px-4 py-2">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)] text-[11px]">
                  {executionResult.rows.map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-[var(--bg-surface-subtle)]">
                      {executionResult.columns.map((c: string) => (
                        <td key={c} className="px-4 py-2 font-semibold text-[var(--text-primary)]">
                          {row[c] !== null && row[c] !== undefined ? String(row[c]) : "null"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Transparent "How this was calculated" section */}
          <div className="p-4 rounded-xl border border-[var(--accent-teal)]/30 bg-[var(--accent-teal-subtle)] space-y-2 text-xs">
            <div className="flex items-center gap-2 font-bold text-[var(--accent-teal-text)]">
              <ShieldCheck className="h-4 w-4" />
              <span>How This Was Calculated (Reproducible Lineage)</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-[11px] pt-1">
              <div>
                <span className="text-[var(--text-muted)] block">Metric Definition:</span>
                <span className="font-semibold text-[var(--text-primary)]">
                  {executionResult.how_calculated?.metric_name} (v{executionResult.how_calculated?.version})
                </span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Source Dataset:</span>
                <span className="font-semibold text-[var(--text-primary)]">
                  {executionResult.how_calculated?.source_dataset}
                </span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Execution Latency:</span>
                <span className="font-mono text-[var(--text-primary)]">
                  {executionResult.how_calculated?.execution_ms} ms
                </span>
              </div>
              <div>
                <span className="text-[var(--text-muted)] block">Executed At:</span>
                <span className="font-mono text-[var(--text-primary)]">
                  {new Date(executionResult.how_calculated?.executed_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Query Audit History */}
      {history.length > 0 && (
        <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border-color)] bg-[var(--bg-surface-subtle)] flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[var(--text-muted)]" />
              Query Audit History
            </span>
            <span className="text-[11px] text-[var(--text-muted)]">Immutable execution trail</span>
          </div>
          <div className="divide-y divide-[var(--border-color)]">
            {history.map((h) => (
              <div key={h.id} className="p-3 text-xs flex items-center justify-between hover:bg-[var(--bg-surface-subtle)]">
                <div>
                  <p className="font-medium text-[var(--text-primary)]">"{h.question}"</p>
                  <pre className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5 truncate max-w-xl">
                    {h.sql}
                  </pre>
                </div>
                <div className="text-right shrink-0 ml-4 font-mono text-[11px]">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">{h.row_count} rows</span>
                  <span className="text-[var(--text-muted)] ml-2">({h.execution_ms}ms)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
