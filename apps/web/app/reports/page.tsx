"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Plus,
  BarChart3,
  TrendingUp,
  Table as TableIcon,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  ChevronRight,
  Loader2
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from "recharts";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [recentQueries, setRecentQueries] = useState<any[]>([]);

  // Widget adding
  const [showAddWidgetModal, setShowAddWidgetModal] = useState(false);
  const [widgetTitle, setWidgetTitle] = useState("");
  const [widgetType, setWidgetType] = useState("bar");
  const [selectedQueryId, setSelectedQueryId] = useState("");

  // Inspect Lineage drawer
  const [inspectedWidget, setInspectedWidget] = useState<any | null>(null);

  async function loadReports() {
    setLoading(true);
    try {
      const [r, q] = await Promise.all([
        fetchApi("/api/v1/reports"),
        fetchApi("/api/v1/query/history?limit=15")
      ]);
      if (Array.isArray(r)) {
        setReports(r);
        if (r.length > 0 && !selectedReport) {
          loadReportDetail(r[0].id);
        }
      }
      if (Array.isArray(q)) {
        setRecentQueries(q);
        if (q.length > 0) setSelectedQueryId(q[0].id);
      }
    } catch (e: any) {
      console.error("Failed to load reports", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReportDetail(id: string) {
    try {
      const detail = await fetchApi(`/api/v1/reports/${id}`);
      setSelectedReport(detail);
    } catch (e: any) {
      console.error("Failed to load report detail", e);
    }
  }

  async function handleCreateReport() {
    if (!newTitle.trim()) return;
    try {
      const res = await fetchApi("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({ title: newTitle.trim(), description: newDesc.trim() })
      });
      setShowCreateModal(false);
      setNewTitle("");
      setNewDesc("");
      await loadReports();
      loadReportDetail(res.id);
    } catch (e: any) {
      alert("Failed to create report: " + e.message);
    }
  }

  async function handleAddWidget() {
    if (!selectedReport?.id || !selectedQueryId) return;
    try {
      await fetchApi(`/api/v1/reports/${selectedReport.id}/widgets`, {
        method: "POST",
        body: JSON.stringify({
          title: widgetTitle || "Verified Metric Widget",
          widget_type: widgetType,
          query_id: selectedQueryId
        })
      });
      setShowAddWidgetModal(false);
      setWidgetTitle("");
      loadReportDetail(selectedReport.id);
    } catch (e: any) {
      alert("Failed to add widget: " + e.message);
    }
  }

  async function handleDeleteReport(id: string) {
    if (!confirm("Are you sure you want to delete this report?")) return;
    try {
      await fetchApi(`/api/v1/reports/${id}`, { method: "DELETE" });
      setSelectedReport(null);
      await loadReports();
    } catch (e: any) {
      alert("Failed to delete report: " + e.message);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <FileText className="h-5 w-5 text-[var(--accent-teal)]" />
            Reports & Dashboards
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Dashboards generated strictly from reproducible queries and approved metrics. Click any chart to inspect its calculation lineage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Report</span>
          </button>
        </div>
      </div>

      {/* Reports Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Saved Reports List */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            Saved Reports ({reports.length})
          </h3>

          {reports.length === 0 && !loading && (
            <div className="p-8 text-center border border-[var(--border-color)] rounded-xl bg-[var(--bg-surface)] space-y-2">
              <FileText className="h-6 w-6 text-[var(--text-muted)] mx-auto opacity-50" />
              <p className="text-xs font-semibold text-[var(--text-primary)]">No reports created yet.</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-xs font-medium text-[var(--accent-teal)] hover:underline"
              >
                Create your first report
              </button>
            </div>
          )}

          <div className="space-y-2">
            {reports.map((r) => {
              const isSelected = selectedReport?.id === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => loadReportDetail(r.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? "border-[var(--accent-teal)] bg-[var(--accent-teal-subtle)]"
                      : "border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)]"
                  }`}
                >
                  <div className="font-semibold text-xs text-[var(--text-primary)] truncate">
                    {r.title}
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[11px] text-[var(--text-muted)]">
                    <span>{r.widget_count} widgets</span>
                    <span>{new Date(r.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Active Report Canvas */}
        <div className="lg:col-span-3 space-y-5">
          {selectedReport ? (
            <div className="space-y-5">
              {/* Report Header */}
              <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">{selectedReport.title}</h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">{selectedReport.description || "Verifiable analytical dashboard"}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowAddWidgetModal(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] hover:bg-[var(--border-color)] text-xs text-[var(--text-primary)] font-medium"
                  >
                    <Plus className="h-3.5 w-3.5 text-[var(--accent-teal)]" />
                    <span>Add Verified Widget</span>
                  </button>
                  <button
                    onClick={() => handleDeleteReport(selectedReport.id)}
                    className="p-1.5 rounded text-[var(--text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                    title="Delete Report"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Widgets Grid */}
              {selectedReport.widgets?.length === 0 ? (
                <div className="p-12 text-center border-2 border-dashed border-[var(--border-color)] rounded-xl bg-[var(--bg-surface)] space-y-3">
                  <BarChart3 className="h-8 w-8 text-[var(--text-muted)] mx-auto opacity-50" />
                  <p className="text-xs font-semibold text-[var(--text-primary)]">No widgets added to this report yet.</p>
                  <p className="text-[11px] text-[var(--text-muted)] max-w-sm mx-auto">
                    Add KPI metric cards, bar charts, or tables backed by verified queries from your Ask Data history.
                  </p>
                  <button
                    onClick={() => setShowAddWidgetModal(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-teal)] text-white text-xs font-medium"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Add First Widget</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedReport.widgets?.map((w: any) => {
                    const rows = w.data?.rows || [];
                    const cols = w.data?.columns || [];
                    const isKpi = w.widget_type === "kpi" || (rows.length === 1 && cols.length === 1);

                    return (
                      <div
                        key={w.id}
                        onClick={() => setInspectedWidget(w)}
                        className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] hover:border-[var(--accent-teal)] cursor-pointer transition-all space-y-3"
                      >
                        <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-2">
                          <span className="text-xs font-bold text-[var(--text-primary)]">{w.title}</span>
                          <span className="text-[10px] font-mono text-[var(--accent-teal-text)] bg-[var(--accent-teal-subtle)] px-2 py-0.5 rounded border border-[var(--accent-teal)]/30 flex items-center gap-1">
                            <ShieldCheck className="h-3 w-3" /> Verified
                          </span>
                        </div>

                        {/* Rendering based on type */}
                        {isKpi ? (
                          <div className="py-4 text-center">
                            <div className="text-3xl font-extrabold text-[var(--accent-teal)]">
                              {rows[0] ? Object.values(rows[0])[0]?.toString() : "—"}
                            </div>
                            <div className="text-[11px] text-[var(--text-muted)] font-mono mt-1">
                              {cols[0]}
                            </div>
                          </div>
                        ) : rows.length > 0 && cols.length >= 2 ? (
                          <div className="h-44 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={rows.slice(0, 10)}>
                                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                <XAxis dataKey={cols[0]} tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
                                <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "var(--bg-surface)",
                                    borderColor: "var(--border-color)",
                                    color: "var(--text-primary)",
                                    fontSize: 11
                                  }}
                                />
                                <Bar dataKey={cols[1]} fill="#0F8B83" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        ) : (
                          <div className="overflow-x-auto max-h-40">
                            <table className="w-full text-left text-[11px] font-mono">
                              <thead className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)]">
                                <tr>
                                  {cols.map((c: string) => (
                                    <th key={c} className="px-2 py-1">{c}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {rows.slice(0, 5).map((r: any, idx: number) => (
                                  <tr key={idx} className="border-t border-[var(--border-color)]">
                                    {cols.map((c: string) => (
                                      <td key={c} className="px-2 py-1 text-[var(--text-primary)]">
                                        {String(r[c])}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        <div className="pt-2 border-t border-[var(--border-color)] flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                          <span>Click to inspect calculation lineage</span>
                          <ChevronRight className="h-3 w-3" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center border border-[var(--border-color)] rounded-xl bg-[var(--bg-surface)] text-xs text-[var(--text-muted)]">
              Select or create a report to view verifiable analytical dashboards.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create Report */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-md p-5 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[var(--text-primary)] border-b border-[var(--border-color)] pb-3">
              Create New Verified Report
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Report Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Executive Financial Overview"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Summary of this report's business intent..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-color)] text-xs text-[var(--text-secondary)]"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateReport}
                disabled={!newTitle.trim()}
                className="px-3 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold disabled:opacity-50"
              >
                Create Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Widget from Executed Queries */}
      {showAddWidgetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-lg p-5 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[var(--text-primary)] border-b border-[var(--border-color)] pb-3">
              Add Verified Widget to Dashboard
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Widget Title</label>
                <input
                  type="text"
                  placeholder="e.g. Revenue by Region"
                  value={widgetTitle}
                  onChange={(e) => setWidgetTitle(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Widget Visualization Type</label>
                <select
                  value={widgetType}
                  onChange={(e) => setWidgetType(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                >
                  <option value="bar">Bar Chart</option>
                  <option value="kpi">KPI Summary Card</option>
                  <option value="table">Data Table</option>
                </select>
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Backing Verified Query</label>
                {recentQueries.length === 0 ? (
                  <p className="text-[11px] text-amber-600">No executed queries in history. Ask a question first in Ask Data.</p>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto border border-[var(--border-color)] rounded-lg p-2 bg-[var(--bg-primary)]">
                    {recentQueries.map((q) => (
                      <div
                        key={q.id}
                        onClick={() => setSelectedQueryId(q.id)}
                        className={`p-2 rounded cursor-pointer border text-[11px] transition-all ${
                          selectedQueryId === q.id
                            ? "border-[var(--accent-teal)] bg-[var(--accent-teal-subtle)] font-semibold"
                            : "border-transparent hover:bg-[var(--bg-surface)]"
                        }`}
                      >
                        <div className="text-[var(--text-primary)]">"{q.question}"</div>
                        <pre className="font-mono text-[10px] text-[var(--text-muted)] truncate">{q.sql}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setShowAddWidgetModal(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-color)] text-xs text-[var(--text-secondary)]"
              >
                Cancel
              </button>
              <button
                onClick={handleAddWidget}
                disabled={!selectedQueryId}
                className="px-3 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold disabled:opacity-50"
              >
                Add Widget
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drill-down Calculation Lineage Modal */}
      {inspectedWidget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-lg p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[var(--accent-teal)]" />
                Calculation Lineage & Metric Audit
              </h3>
              <button onClick={() => setInspectedWidget(null)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[var(--text-muted)] block">Widget Title:</span>
                <span className="font-bold text-[var(--text-primary)]">{inspectedWidget.title}</span>
              </div>

              {inspectedWidget.data?.sql && (
                <div>
                  <span className="text-[var(--text-muted)] block mb-1">Underlying Executed SQL:</span>
                  <pre className="p-2.5 rounded bg-[var(--bg-surface-subtle)] border border-[var(--border-color)] font-mono text-[11px] text-[var(--accent-teal-text)] overflow-x-auto whitespace-pre-wrap">
                    {inspectedWidget.data.sql}
                  </pre>
                </div>
              )}

              {inspectedWidget.data?.how_calculated && (
                <div className="p-3 rounded-lg bg-[var(--accent-teal-subtle)] border border-[var(--accent-teal)]/30 space-y-1.5">
                  <div className="font-semibold text-[var(--accent-teal-text)]">Business Definition:</div>
                  <div className="text-[11px] text-[var(--text-primary)]">
                    Metric: <span className="font-bold">{inspectedWidget.data.how_calculated.metric_name}</span> (v{inspectedWidget.data.how_calculated.version})
                  </div>
                  <div className="text-[11px] text-[var(--text-primary)]">
                    Source: {inspectedWidget.data.how_calculated.source_dataset}
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)] font-mono">
                    Executed at: {new Date(inspectedWidget.data.how_calculated.timestamp || Date.now()).toLocaleString()}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setInspectedWidget(null)}
                className="px-3 py-1.5 rounded bg-[var(--bg-surface-subtle)] hover:bg-[var(--border-color)] text-xs text-[var(--text-primary)] font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
