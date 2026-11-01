"use client";

import { useState, useEffect } from "react";
import {
  BookOpen,
  Plus,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ChevronRight,
  ShieldCheck,
  Tag,
  Trash2
} from "lucide-react";
import { fetchApi } from "@/lib/api";

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<"metrics" | "terms">("metrics");
  const [metrics, setMetrics] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // New Metric Form State
  const [showMetricModal, setShowMetricModal] = useState(false);
  const [metricForm, setMetricForm] = useState({
    name: "",
    description: "",
    formula_sql: "",
    grain: "order",
    time_column: "created_at",
    allowed_dimensions: "region, plan, channel",
    unit: "USD",
    currency: "$",
    status: "approved"
  });

  // New Term Form State
  const [showTermModal, setShowTermModal] = useState(false);
  const [termForm, setTermForm] = useState({
    name: "",
    definition: "",
    synonyms: "",
    related_table: "orders",
    related_column: "status",
  });

  async function loadKnowledge() {
    setLoading(true);
    try {
      const [m, t] = await Promise.all([
        fetchApi("/api/v1/knowledge/metrics"),
        fetchApi("/api/v1/knowledge/terms"),
      ]);
      if (Array.isArray(m)) setMetrics(m);
      if (Array.isArray(t)) setTerms(t);
    } catch (e: any) {
      console.error("Failed to load knowledge", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadKnowledge();
  }, []);

  async function handleCreateMetric() {
    if (!metricForm.name || !metricForm.formula_sql) return;
    try {
      await fetchApi("/api/v1/knowledge/metrics", {
        method: "POST",
        body: JSON.stringify({
          ...metricForm,
          allowed_dimensions: metricForm.allowed_dimensions.split(",").map(d => d.trim()).filter(Boolean),
          source_tables: ["source_data"]
        })
      });
      setShowMetricModal(false);
      setMetricForm({
        name: "",
        description: "",
        formula_sql: "",
        grain: "order",
        time_column: "created_at",
        allowed_dimensions: "region, plan, channel",
        unit: "USD",
        currency: "$",
        status: "approved"
      });
      await loadKnowledge();
    } catch (e: any) {
      alert("Failed to save metric definition: " + e.message);
    }
  }

  async function handleCreateTerm() {
    if (!termForm.name || !termForm.definition) return;
    try {
      await fetchApi("/api/v1/knowledge/terms", {
        method: "POST",
        body: JSON.stringify({
          ...termForm,
          synonyms: termForm.synonyms.split(",").map(s => s.trim()).filter(Boolean)
        })
      });
      setShowTermModal(false);
      setTermForm({ name: "", definition: "", synonyms: "", related_table: "orders", related_column: "status" });
      await loadKnowledge();
    } catch (e: any) {
      alert("Failed to save glossary term: " + e.message);
    }
  }

  async function handleApproveMetric(id: string) {
    try {
      await fetchApi(`/api/v1/knowledge/metrics/${id}/approve`, { method: "POST" });
      await loadKnowledge();
    } catch (e: any) {
      alert("Failed to approve metric: " + e.message);
    }
  }

  async function handleSubmitReview(id: string) {
    try {
      await fetchApi(`/api/v1/knowledge/metrics/${id}/submit-review`, { method: "POST" });
      await loadKnowledge();
    } catch (e: any) {
      alert("Failed to submit metric for review: " + e.message);
    }
  }

  async function handleApproveTerm(id: string) {
    try {
      await fetchApi(`/api/v1/knowledge/terms/${id}/approve`, { method: "POST" });
      await loadKnowledge();
    } catch (e: any) {
      alert("Failed to approve term: " + e.message);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-[var(--accent-teal)]" />
            Business Knowledge & Metrics Layer
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Define approved business formulas, glossary terms, and join constraints. Natural language queries resolve directly to these vetted definitions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === "metrics" ? (
            <button
              onClick={() => setShowMetricModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Metric Definition</span>
            </button>
          ) : (
            <button
              onClick={() => setShowTermModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Glossary Term</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[var(--border-color)] pb-2">
        <button
          onClick={() => setActiveTab("metrics")}
          className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
            activeTab === "metrics"
              ? "bg-[var(--accent-teal-subtle)] text-[var(--accent-teal-text)] border border-[var(--accent-teal)]"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)]"
          }`}
        >
          Approved Metrics ({metrics.length})
        </button>
        <button
          onClick={() => setActiveTab("terms")}
          className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
            activeTab === "terms"
              ? "bg-[var(--accent-teal-subtle)] text-[var(--accent-teal-text)] border border-[var(--accent-teal)]"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)]"
          }`}
        >
          Business Glossary ({terms.length})
        </button>
      </div>

      {/* Tab: Metrics */}
      {activeTab === "metrics" && (
        <div className="space-y-4">
          {metrics.length === 0 && !loading && (
            <div className="p-12 text-center border border-[var(--border-color)] rounded-xl bg-[var(--bg-surface)] space-y-3">
              <BookOpen className="h-8 w-8 text-[var(--text-muted)] mx-auto opacity-50" />
              <p className="text-xs font-semibold text-[var(--text-primary)]">No metric definitions yet.</p>
              <p className="text-[11px] text-[var(--text-muted)] max-w-sm mx-auto">
                Define measurable business metrics (such as Net Revenue, ARPU, or Churn Rate) so natural language questions calculate deterministic answers.
              </p>
              <button
                onClick={() => setShowMetricModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-teal)] text-white text-xs font-medium"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Define First Metric</span>
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {metrics.map((m) => (
              <div
                key={m.id}
                className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] hover:border-[var(--border-hover)] transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      {m.name}
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[var(--bg-surface-subtle)] text-[var(--text-muted)] border border-[var(--border-color)]">
                        v{m.version}
                      </span>
                    </h3>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{m.description || "No description provided."}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {m.status === "draft" && (
                      <button
                        onClick={() => handleSubmitReview(m.id)}
                        className="text-[10px] px-2 py-0.5 rounded border border-[var(--border-color)] bg-[var(--bg-surface-subtle)] hover:bg-[var(--bg-primary)] text-[var(--text-primary)]"
                      >
                        Submit Review
                      </button>
                    )}
                    {m.status !== "approved" && (
                      <button
                        onClick={() => handleApproveMetric(m.id)}
                        className="text-[10px] px-2 py-0.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white font-medium shadow-sm"
                      >
                        Approve
                      </button>
                    )}
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      m.status === "approved"
                        ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                        : m.status === "in_review"
                        ? "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-800"
                        : "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                    }`}>
                      {m.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded bg-[var(--bg-surface-subtle)] border border-[var(--border-color)]">
                  <div className="text-[10px] font-bold text-[var(--text-muted)] uppercase mb-1">Approved Formula:</div>
                  <pre className="text-xs font-mono text-[var(--accent-teal-text)] overflow-x-auto">
                    {m.formula_sql}
                  </pre>
                </div>

                <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-[var(--text-secondary)]">
                  <div>
                    <span className="text-[var(--text-muted)]">Grain:</span> {m.grain}
                  </div>
                  <div>
                    <span className="text-[var(--text-muted)]">Unit:</span> {m.unit}
                  </div>
                  <div>
                    <span className="text-[var(--text-muted)]">Owner:</span> {m.owner}
                  </div>
                </div>

                {m.allowed_dimensions?.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1 text-[10px]">
                    <span className="text-[var(--text-muted)]">Dimensions:</span>
                    {m.allowed_dimensions.map((dim: string) => (
                      <span key={dim} className="px-1.5 py-0.5 rounded bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono">
                        {dim}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Glossary */}
      {activeTab === "terms" && (
        <div className="space-y-4">
          {terms.length === 0 && !loading && (
            <div className="p-12 text-center border border-[var(--border-color)] rounded-xl bg-[var(--bg-surface)] space-y-3">
              <Tag className="h-8 w-8 text-[var(--text-muted)] mx-auto opacity-50" />
              <p className="text-xs font-semibold text-[var(--text-primary)]">No glossary terms created yet.</p>
              <p className="text-[11px] text-[var(--text-muted)] max-w-sm mx-auto">
                Add business terms, plain-English definitions, and synonyms so users can ask questions using company-specific vocabulary.
              </p>
              <button
                onClick={() => setShowTermModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-teal)] text-white text-xs font-medium"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add First Term</span>
              </button>
            </div>
          )}

          <div className="divide-y divide-[var(--border-color)] rounded-xl border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
            {terms.map((t) => (
              <div key={t.id} className="p-4 hover:bg-[var(--bg-surface-subtle)] transition-colors flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--text-primary)]">{t.name}</span>
                    <span className={`text-[10px] font-semibold px-2 py-0.2 rounded-full border ${
                      t.status === "approved"
                        ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-700"
                    }`}>
                      {t.status}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">{t.definition}</p>
                  {t.synonyms?.length > 0 && (
                    <div className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] pt-1">
                      <span className="font-medium">Synonyms:</span>
                      {t.synonyms.map((s: string) => (
                        <span key={s} className="px-1.5 py-0.2 rounded bg-[var(--bg-surface-subtle)] border border-[var(--border-color)] font-mono text-[10px]">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {t.status !== "approved" && (
                  <button
                    onClick={() => handleApproveTerm(t.id)}
                    className="px-2.5 py-1 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-[11px] font-semibold shrink-0"
                  >
                    Approve Term
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal: New Metric Definition */}
      {showMetricModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-lg p-5 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[var(--text-primary)] border-b border-[var(--border-color)] pb-3">
              Define Business Metric
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Metric Name</label>
                <input
                  type="text"
                  placeholder="e.g. Net Revenue"
                  value={metricForm.name}
                  onChange={(e) => setMetricForm({ ...metricForm, name: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Plain-English Description</label>
                <textarea
                  rows={2}
                  placeholder="Explain exactly how this metric is defined in your company..."
                  value={metricForm.description}
                  onChange={(e) => setMetricForm({ ...metricForm, description: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Approved SQL Expression / Formula</label>
                <input
                  type="text"
                  placeholder="e.g. SUM(amount) or COUNT(DISTINCT customer_id)"
                  value={metricForm.formula_sql}
                  onChange={(e) => setMetricForm({ ...metricForm, formula_sql: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Calculation Grain</label>
                  <input
                    type="text"
                    placeholder="order / customer"
                    value={metricForm.grain}
                    onChange={(e) => setMetricForm({ ...metricForm, grain: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Unit / Currency</label>
                  <input
                    type="text"
                    value={metricForm.unit}
                    onChange={(e) => setMetricForm({ ...metricForm, unit: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Allowed Dimensions (comma separated)</label>
                <input
                  type="text"
                  placeholder="region, plan, channel"
                  value={metricForm.allowed_dimensions}
                  onChange={(e) => setMetricForm({ ...metricForm, allowed_dimensions: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setShowMetricModal(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-color)] text-xs text-[var(--text-secondary)]"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMetric}
                disabled={!metricForm.name || !metricForm.formula_sql}
                className="px-3 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold disabled:opacity-50"
              >
                Save & Approve Metric
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: New Glossary Term */}
      {showTermModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-md p-5 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[var(--text-primary)] border-b border-[var(--border-color)] pb-3">
              Add Glossary Term
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Term Name</label>
                <input
                  type="text"
                  placeholder="e.g. Paid Order"
                  value={termForm.name}
                  onChange={(e) => setTermForm({ ...termForm, name: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Plain-English Definition</label>
                <textarea
                  rows={3}
                  placeholder="Explain what qualifies as this term..."
                  value={termForm.definition}
                  onChange={(e) => setTermForm({ ...termForm, definition: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Synonyms (comma separated)</label>
                <input
                  type="text"
                  placeholder="successful order, captured payment"
                  value={termForm.synonyms}
                  onChange={(e) => setTermForm({ ...termForm, synonyms: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setShowTermModal(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-color)] text-xs text-[var(--text-secondary)]"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTerm}
                disabled={!termForm.name || !termForm.definition}
                className="px-3 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold disabled:opacity-50"
              >
                Save Term
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
