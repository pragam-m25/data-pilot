"use client";

import { useState, useEffect, useRef } from "react";
import {
  Upload,
  Database,
  CheckCircle2,
  AlertTriangle,
  X,
  Plus,
  Loader2,
  Table,
  ShieldCheck,
  RefreshCw,
  Trash2
} from "lucide-react";
import { fetchApi } from "@/lib/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [selectedSource, setSelectedSource] = useState<any | null>(null);
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: any[] } | null>(null);
  const [profileData, setProfileData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [attachingTable, setAttachingTable] = useState<string | null>(null);

  // PostgreSQL connection modal
  const [showPgModal, setShowPgModal] = useState(false);
  const [pgForm, setPgForm] = useState({
    name: "Production Postgres",
    host: "localhost",
    port: 5432,
    database: "analytics",
    username: "readonly_user",
    password: "",
    schema_name: "public"
  });
  const [pgTesting, setPgTesting] = useState(false);
  const [pgError, setPgError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadSources() {
    setLoading(true);
    try {
      const [srcData, connData] = await Promise.all([
        fetchApi("/api/v1/sources").catch(() => []),
        fetchApi("/api/v1/connections").catch(() => [])
      ]);
      if (Array.isArray(srcData)) {
        setSources(srcData);
        if (srcData.length > 0 && !selectedSource) {
          selectSource(srcData[0].id);
        }
      }
      if (Array.isArray(connData)) {
        setConnections(connData);
      }
    } catch (e: any) {
      console.error("Failed to load sources", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
  }, []);

  async function selectSource(id: string) {
    try {
      const detail = await fetchApi(`/api/v1/sources/${id}`);
      setSelectedSource(detail);

      // Load real preview
      const preview = await fetchApi(`/api/v1/sources/${id}/preview?limit=20`);
      setPreviewData(preview);

      // Load deterministic profile (IQR outliers, duplicate rows, quality checks)
      const profile = await fetchApi(`/api/v1/sources/${id}/profile`);
      setProfileData(profile);
    } catch (e: any) {
      console.error("Failed to load source details", e);
    }
  }

  async function handleFileUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", file.name);

    try {
      const uploaded = await fetchApi("/api/v1/sources/upload", {
        method: "POST",
        body: formData,
      });

      await loadSources();
      if (uploaded?.id) {
        selectSource(uploaded.id);
      }
    } catch (e: any) {
      setUploadError(e.message || "Failed to parse file.");
    } finally {
      setUploading(false);
    }
  }

  async function handleAttachTable(connId: string, tableName: string) {
    setAttachingTable(`${connId}_${tableName}`);
    try {
      const res = await fetchApi("/api/v1/sources/from-connection", {
        method: "POST",
        body: JSON.stringify({
          connection_id: connId,
          table_name: tableName,
        }),
      });
      await loadSources();
      if (res?.id) {
        selectSource(res.id);
      }
    } catch (e: any) {
      alert("Failed to attach database table: " + e.message);
    } finally {
      setAttachingTable(null);
    }
  }

  async function handleTestPgConnection() {
    setPgTesting(true);
    setPgError(null);
    try {
      const res = await fetchApi("/api/v1/connections", {
        method: "POST",
        body: JSON.stringify(pgForm),
      });
      setShowPgModal(false);
      await loadSources();
    } catch (e: any) {
      setPgError(e.message || "Failed to establish PostgreSQL connection.");
    } finally {
      setPgTesting(false);
    }
  }

  async function handleDeleteSource(id: string) {
    if (!confirm("Are you sure you want to remove this data source?")) return;
    try {
      await fetchApi(`/api/v1/sources/${id}`, { method: "DELETE" });
      setSelectedSource(null);
      setPreviewData(null);
      setProfileData(null);
      await loadSources();
    } catch (e: any) {
      alert("Failed to delete source: " + e.message);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <Database className="h-5 w-5 text-[var(--accent-teal)]" />
            Data Sources & Quality Inspection
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Ingest verifiable CSV/XLSX files and PostgreSQL databases. Calculations performed deterministically with DuckDB.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPgModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)] text-[var(--text-primary)] text-xs font-medium"
          >
            <Plus className="h-3.5 w-3.5 text-[var(--accent-teal)]" />
            <span>Connect PostgreSQL</span>
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold shadow-sm"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Upload File</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
          />
        </div>
      </div>

      {/* Upload Error Banner */}
      {uploadError && (
        <div className="p-3 rounded-lg border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/30 text-xs text-red-800 dark:text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
          <button onClick={() => setUploadError(null)} className="hover:opacity-75">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Uploading progress indicator */}
      {uploading && (
        <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] flex items-center gap-3">
          <Loader2 className="h-4 w-4 text-[var(--accent-teal)] animate-spin" />
          <span className="text-xs text-[var(--text-primary)]">
            Parsing actual bytes with DuckDB, detecting schema, and calculating column distributions...
          </span>
        </div>
      )}

      {/* Main Split View: Sources List on Left, Active Inspection on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Sources List */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            Configured Sources ({sources.length})
          </h3>

          {sources.length === 0 && !loading && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[var(--border-color)] hover:border-[var(--accent-teal)] rounded-xl p-8 text-center cursor-pointer bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)] transition-all space-y-2"
            >
              <Upload className="h-8 w-8 text-[var(--text-muted)] mx-auto" />
              <p className="text-xs font-semibold text-[var(--text-primary)]">Drop CSV or XLSX file here</p>
              <p className="text-[11px] text-[var(--text-muted)]">Supports delimited files up to 100MB</p>
            </div>
          )}

          <div className="space-y-2">
            {sources.map((src) => {
              const isSelected = selectedSource?.id === src.id;
              return (
                <div
                  key={src.id}
                  onClick={() => selectSource(src.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? "border-[var(--accent-teal)] bg-[var(--accent-teal-subtle)]"
                      : "border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-subtle)]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-xs text-[var(--text-primary)] truncate max-w-[180px]">
                      {src.name}
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--bg-surface-subtle)] border border-[var(--border-color)] text-[var(--text-muted)] uppercase">
                      {src.file_type}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-[11px] text-[var(--text-secondary)] font-mono">
                    <span>{src.row_count?.toLocaleString()} rows</span>
                    <span>{src.column_count} cols</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Database Connections Section */}
          <div className="pt-4 border-t border-[var(--border-color)] space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                Database Connections ({connections.length})
              </h3>
            </div>

            {connections.length === 0 ? (
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] text-center text-[11px] text-[var(--text-muted)]">
                No external databases attached.
              </div>
            ) : (
              <div className="space-y-2">
                {connections.map((conn) => {
                  return (
                    <div key={conn.id} className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-[var(--text-primary)] flex items-center gap-1.5">
                          <Database className="h-3 w-3 text-[var(--accent-teal)]" />
                          {conn.name}
                        </span>
                        <span className="text-[10px] font-mono text-[var(--accent-teal)]">
                          {conn.table_count} tables
                        </span>
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] font-mono">
                        {conn.database}@{conn.host}:{conn.port}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Inspection, Quality & Schema */}
        <div className="lg:col-span-2 space-y-5">
          {selectedSource ? (
            <div className="space-y-5">
              {/* Source Header Summary */}
              <div className="p-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-[var(--text-primary)]">{selectedSource.name}</h2>
                  <p className="text-[11px] text-[var(--text-secondary)] font-mono mt-0.5">
                    {selectedSource.row_count?.toLocaleString()} verified rows · {selectedSource.column_count} columns · Status: Ready
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteSource(selectedSource.id)}
                  className="p-1.5 rounded text-[var(--text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                  title="Delete Source"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {/* Data Quality Checks Card */}
              {profileData && (
                <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-[var(--border-color)] bg-[var(--bg-surface-subtle)] flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-[var(--accent-teal)]" />
                      Data Quality Validation Checks ({profileData.quality_checks?.length || 0})
                    </span>
                    <span className="text-[11px] font-mono text-[var(--text-secondary)]">
                      Exact Duplicates: {profileData.duplicate_rows} rows
                    </span>
                  </div>
                  <div className="divide-y divide-[var(--border-color)] max-h-60 overflow-y-auto">
                    {profileData.quality_checks?.map((check: any, idx: number) => (
                      <div key={idx} className="p-3 text-xs flex items-center justify-between hover:bg-[var(--bg-surface-subtle)]">
                        <div className="flex items-center gap-2.5">
                          {check.status === "pass" ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                          )}
                          <div>
                            <span className="font-semibold text-[var(--text-primary)]">{check.check_name}</span>
                            <span className="ml-2 font-mono text-[10px] text-[var(--text-muted)]">Rule: {check.rule}</span>
                            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{check.sample_impact}</p>
                          </div>
                        </div>
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[var(--bg-surface-subtle)] border border-[var(--border-color)] text-[var(--text-primary)]">
                          {check.actual_value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Inferred Column Profiles */}
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
                <div className="px-4 py-2.5 border-b border-[var(--border-color)] bg-[var(--bg-surface-subtle)] flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                    Schema & Descriptive Statistics
                  </span>
                  <span className="text-[11px] text-[var(--text-muted)]">Calculated with DuckDB</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border-b border-[var(--border-color)]">
                      <tr>
                        <th className="px-3 py-2">Column</th>
                        <th className="px-3 py-2">Inferred Type</th>
                        <th className="px-3 py-2">Null Count</th>
                        <th className="px-3 py-2">Distinct</th>
                        <th className="px-3 py-2">Min / Max</th>
                        <th className="px-3 py-2">Mean ± Std</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-color)] font-mono text-[11px]">
                      {selectedSource.columns?.map((col: any) => (
                        <tr key={col.id} className="hover:bg-[var(--bg-surface-subtle)]">
                          <td className="px-3 py-2 font-semibold text-[var(--text-primary)]">{col.name}</td>
                          <td className="px-3 py-2 text-[var(--text-muted)]">{col.inferred_type}</td>
                          <td className="px-3 py-2">
                            {col.null_count > 0 ? (
                              <span className="text-amber-600 dark:text-amber-400 font-bold">{col.null_count} ({col.null_pct}%)</span>
                            ) : (
                              <span className="text-emerald-600 dark:text-emerald-400">0</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">{col.distinct_count?.toLocaleString()}</td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">
                            {col.min !== null && col.min !== undefined ? `${col.min} .. ${col.max}` : "—"}
                          </td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">
                            {col.mean !== null && col.mean !== undefined ? `${col.mean} ± ${col.std || 0}` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Real Row Preview */}
              {previewData && (
                <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-surface)] overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-[var(--border-color)] bg-[var(--bg-surface-subtle)] flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
                      <Table className="h-3.5 w-3.5 text-[var(--accent-teal)]" />
                      Preview Raw Records (First {previewData.rows.length} of {previewData.rows.length} fetched)
                    </span>
                  </div>
                  <div className="overflow-x-auto max-h-60">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border-b border-[var(--border-color)] sticky top-0">
                        <tr>
                          {previewData.columns.map((col) => (
                            <th key={col} className="px-3 py-2 whitespace-nowrap">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-color)] text-[11px]">
                        {previewData.rows.map((r, i) => (
                          <tr key={i} className="hover:bg-[var(--bg-surface-subtle)]">
                            {previewData.columns.map((c) => (
                              <td key={c} className="px-3 py-1.5 whitespace-nowrap text-[var(--text-primary)]">
                                {r[c] !== null && r[c] !== undefined ? String(r[c]) : <span className="text-[var(--text-muted)] italic">null</span>}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center border border-[var(--border-color)] rounded-lg bg-[var(--bg-surface)] text-[var(--text-muted)] text-xs">
              Select or upload a data source to inspect its verified schema and quality metrics.
            </div>
          )}
        </div>
      </div>

      {/* Real PostgreSQL Connection Modal */}
      {showPgModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-xl w-full max-w-md p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Database className="h-4 w-4 text-[var(--accent-teal)]" />
                Connect Real PostgreSQL Database
              </h3>
              <button onClick={() => setShowPgModal(false)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                <X className="h-4 w-4" />
              </button>
            </div>

            {pgError && (
              <div className="p-2.5 rounded bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs">
                {pgError}
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-medium mb-1">Connection Name</label>
                <input
                  type="text"
                  value={pgForm.name}
                  onChange={(e) => setPgForm({ ...pgForm, name: e.target.value })}
                  className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Host</label>
                  <input
                    type="text"
                    value={pgForm.host}
                    onChange={(e) => setPgForm({ ...pgForm, host: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Port</label>
                  <input
                    type="number"
                    value={pgForm.port}
                    onChange={(e) => setPgForm({ ...pgForm, port: parseInt(e.target.value) || 5432 })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Database</label>
                  <input
                    type="text"
                    value={pgForm.database}
                    onChange={(e) => setPgForm({ ...pgForm, database: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Schema</label>
                  <input
                    type="text"
                    value={pgForm.schema_name}
                    onChange={(e) => setPgForm({ ...pgForm, schema_name: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Username</label>
                  <input
                    type="text"
                    value={pgForm.username}
                    onChange={(e) => setPgForm({ ...pgForm, username: e.target.value })}
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
                <div>
                  <label className="block text-[var(--text-secondary)] font-medium mb-1">Password</label>
                  <input
                    type="password"
                    value={pgForm.password}
                    onChange={(e) => setPgForm({ ...pgForm, password: e.target.value })}
                    placeholder="••••••••"
                    className="w-full px-3 py-1.5 rounded border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-teal)]"
                  />
                </div>
              </div>

              <p className="text-[11px] text-[var(--text-muted)]">
                Tested against the PostgreSQL server before saving. Password encrypted with AES-256 and never logged or exposed to the client.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-color)] pt-3">
              <button
                onClick={() => setShowPgModal(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)]"
              >
                Cancel
              </button>
              <button
                onClick={handleTestPgConnection}
                disabled={pgTesting || !pgForm.database || !pgForm.username}
                className="px-3 py-1.5 rounded bg-[var(--accent-teal)] hover:bg-[var(--accent-teal-hover)] text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              >
                {pgTesting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                <span>Test & Save Connection</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
