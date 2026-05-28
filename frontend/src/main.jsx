import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BarChart3, Bell, Check, ClipboardList, Database, FileText, FileUp, Leaf, Lock, RefreshCw, Search, Settings, ShieldCheck, TriangleAlert, Users, X } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function App() {
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ source: "", status: "", scope: "", flag: "", search: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    return params.toString();
  }, [filters]);

  async function refresh() {
    try {
      setError("");
      const [summaryRes, recordsRes, batchesRes] = await Promise.all([
        fetch(`${API_BASE}/summary/`),
        fetch(`${API_BASE}/activities/${query ? `?${query}` : ""}`),
        fetch(`${API_BASE}/batches/`),
      ]);
      if (!summaryRes.ok || !recordsRes.ok || !batchesRes.ok) {
        throw new Error("API returned an error while loading review data.");
      }
      const [summaryData, recordsData, batchesData] = await Promise.all([summaryRes.json(), recordsRes.json(), batchesRes.json()]);
      setSummary(summaryData);
      setRecords(Array.isArray(recordsData) ? recordsData : []);
      setBatches(Array.isArray(batchesData) ? batchesData : []);
    } catch (loadError) {
      setError(`${loadError.message} Confirm the Django backend is running on port 8000.`);
      setRecords([]);
      setBatches([]);
    }
  }

  useEffect(() => {
    refresh();
  }, [query]);

  async function upload(kind, file) {
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    const endpoint = kind === "sap" ? "upload-sap" : "upload-utility";
    const res = await fetch(`${API_BASE}/batches/${endpoint}/`, { method: "POST", body: form });
    setMessage(res.ok ? `Imported ${file.name}` : "Import failed");
    await refresh();
    setBusy(false);
  }

  async function importConcur() {
    setBusy(true);
    const res = await fetch(`${API_BASE}/batches/import-concur/`, { method: "POST" });
    setMessage(res.ok ? "Pulled mock Concur itineraries" : "Concur import failed");
    await refresh();
    setBusy(false);
  }

  async function seed() {
    setBusy(true);
    await fetch(`${API_BASE}/seed-samples/`, { method: "POST" });
    setMessage("Demo sample data reset");
    await refresh();
    setBusy(false);
  }

  async function review(id, action) {
    const res = await fetch(`${API_BASE}/activities/${id}/${action}/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const data = await res.json();
    if (res.ok) {
      setSelected(data);
      setMessage(action === "approve" ? "Record approved and locked" : "Record rejected");
      await refresh();
    } else {
      setMessage(data.detail || "Review action failed");
    }
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="portal-main">
        <header className="portal-header">
          <div>
            <p className="eyebrow">Breathe ESG - Portal</p>
            <h1>Hello, Analyst [Full Name] - ESG Review Center</h1>
          </div>
          <div className="header-actions">
            <button className="icon-button ghost" onClick={refresh} title="Refresh dashboard">
              <RefreshCw size={18} />
            </button>
            <button className="icon-button ghost" title="Notifications">
              <Bell size={18} />
            </button>
            <div className="avatar">A</div>
            <span>Hello, [Analyst Name]</span>
          </div>
        </header>

        <main className="workspace">
          <section className="left-pane">
            <Stats summary={summary} />
            <ImportPanel busy={busy} upload={upload} importConcur={importConcur} seed={seed} message={message} />
            <section className="review-card">
              <div className="review-card-head">
                <h2>Multi-Tenant Data Ingestion Status</h2>
                <FilterBar filters={filters} setFilters={setFilters} />
              </div>
              {error && <div className="error-banner"><TriangleAlert size={16} /> {error}</div>}
              <RecordTable records={records} selected={selected} setSelected={setSelected} seed={seed} busy={busy} />
            </section>
          </section>
          <aside className="right-pane">
            <DetailPanel record={selected} review={review} />
            <BatchList batches={batches} />
          </aside>
        </main>
      </div>
    </div>
  );
}

function Sidebar() {
  const items = [
    ["Dashboard", BarChart3],
    ["Data Streams", Database],
    ["Compliance Reports", FileText],
    ["Tenant Manager", Users],
    ["Audit Logs", ClipboardList],
    ["Settings", Settings],
  ];
  return (
    <aside className="sidebar">
      <div className="brand-mark">
        <div className="leaf-badge"><Leaf size={28} /></div>
        <strong>BESG</strong>
      </div>
      <nav>
        {items.map(([label, Icon], index) => (
          <a className={index === 0 ? "active" : ""} href="#" key={label}>
            <Icon size={16} />
            {label}
          </a>
        ))}
      </nav>
      <div className="sidebar-illustration">
        <Leaf size={54} />
      </div>
    </aside>
  );
}

function Stats({ summary }) {
  const total = summary?.total ?? 0;
  const failed = summary?.failed ?? 0;
  const integrity = total ? Math.max(0, Math.round(((total - failed) / total) * 100)) : 100;
  const items = [
    ["Total Active Tenants", "1", BarChart3, "trend"],
    ["Data Integrity Score", `${integrity}%`, ShieldCheck, "gauge"],
    ["Current Pending Audits", summary?.pending ?? 0, TriangleAlert, "alert"],
  ];
  return (
    <section className="stats-grid">
      {items.map(([label, value, Icon, tone]) => (
        <div className={`stat ${tone}`} key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <Icon size={32} />
        </div>
      ))}
    </section>
  );
}

function ImportPanel({ busy, upload, importConcur, seed, message }) {
  return (
    <section className="import-band">
      <label className="upload-control">
        <FileUp size={18} />
        SAP CSV
        <input type="file" accept=".csv" disabled={busy} onChange={(event) => upload("sap", event.target.files[0])} />
      </label>
      <label className="upload-control">
        <FileUp size={18} />
        Utility CSV
        <input type="file" accept=".csv" disabled={busy} onChange={(event) => upload("utility", event.target.files[0])} />
      </label>
      <button onClick={importConcur} disabled={busy}>
        <Database size={18} />
        Pull Concur
      </button>
      <button onClick={seed} disabled={busy}>
        <RefreshCw size={18} />
        Reset Demo
      </button>
      <span className="message">{message}</span>
    </section>
  );
}

function FilterBar({ filters, setFilters }) {
  const set = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  return (
    <section className="filters">
      <div className="search-box">
        <Search size={16} />
        <input value={filters.search} onChange={(event) => set("search", event.target.value)} placeholder="Search source id or description" />
      </div>
      <select value={filters.source} onChange={(event) => set("source", event.target.value)}>
        <option value="">All sources</option>
        <option value="sap">SAP</option>
        <option value="utility">Utility</option>
        <option value="concur">Concur</option>
      </select>
      <select value={filters.status} onChange={(event) => set("status", event.target.value)}>
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="failed">Failed</option>
      </select>
      <select value={filters.scope} onChange={(event) => set("scope", event.target.value)}>
        <option value="">All scopes</option>
        <option value="scope_1">Scope 1</option>
        <option value="scope_2">Scope 2</option>
        <option value="scope_3">Scope 3</option>
      </select>
      <input className="flag-filter" value={filters.flag} onChange={(event) => set("flag", event.target.value)} placeholder="flag name" />
    </section>
  );
}

function RecordTable({ records, selected, setSelected, seed, busy }) {
  return (
    <section className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Source</th>
            <th>Record</th>
            <th>Scope</th>
            <th>Activity</th>
            <th>Normalized</th>
            <th>kgCO2e</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {!records.length && (
            <tr>
              <td colSpan="8">
                <div className="empty-table-state">
                  <Database size={22} />
                  <strong>No ingestion records loaded</strong>
                  <span>Start the Django backend, then reset demo data or upload a source file.</span>
                  <button onClick={seed} disabled={busy}>
                    <RefreshCw size={16} />
                    Reset Demo
                  </button>
                </div>
              </td>
            </tr>
          )}
          {records.map((record) => (
            <tr key={record.id} className={selected?.id === record.id ? "selected" : ""} onClick={() => setSelected(record)}>
              <td>
                <Badge tone={record.status}>{record.status}</Badge>
                {record.is_locked && <Lock size={14} style={{ marginLeft: "6px", verticalAlign: "middle", color: "var(--accent)" }} />}
              </td>
              <td>{record.source.kind}</td>
              <td><code>{record.source_row_id}</code></td>
              <td>{record.scope.replace("_", " ")}</td>
              <td>
                <div style={{ fontWeight: 500 }}>{record.description}</div>
                {record.flags.length > 0 && (
                  <small style={{ alignItems: "center", color: "var(--yellow)", display: "inline-flex", gap: "4px", marginTop: "4px" }}>
                    <TriangleAlert size={13} />
                    {record.flags.length} quality warnings
                  </small>
                )}
              </td>
              <td><strong>{record.normalized_quantity ?? "-"}</strong> <small>{record.normalized_unit}</small></td>
              <td>{record.estimated_kg_co2e != null ? `${(record.estimated_kg_co2e / 1000).toFixed(2)} tCO2e` : "-"}</td>
              <td>{record.flags.length ? <Badge tone="flag">{record.flags.length}</Badge> : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function DetailPanel({ record, review }) {
  if (!record) {
    return <section className="detail empty"><Database size={24} /><p>Select a row to inspect source evidence, flags, and audit events.</p></section>;
  }
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <p className="eyebrow">{record.source.kind} / {record.scope}</p>
          <h2>{record.description}</h2>
        </div>
        {record.is_locked && <Badge tone="approved">Locked</Badge>}
      </div>
      <div className="action-row">
        <button onClick={() => review(record.id, "approve")} disabled={record.is_locked || record.status === "failed"}>
          <Check size={18} /> Approve
        </button>
        <button className="secondary" onClick={() => review(record.id, "reject")} disabled={record.is_locked}>
          <X size={18} /> Reject
        </button>
      </div>
      <dl className="kv">
        <dt>Source row</dt><dd>{record.source_row_id}</dd>
        <dt>Facility</dt><dd>{record.facility?.name || "Unmapped"}</dd>
        <dt>Period</dt><dd>{record.period_start || "-"} to {record.period_end || "-"}</dd>
        <dt>Normalized</dt><dd>{record.normalized_quantity ?? "-"} {record.normalized_unit}</dd>
        <dt>Estimate</dt><dd>{record.estimated_kg_co2e ?? "-"} kgCO2e</dd>
      </dl>
      <h3>Emission Factor Provenance</h3>
      <div style={{ background: "#f0eee8", padding: "10px", borderRadius: "6px", fontSize: "12px", color: "var(--ink)", marginTop: "6px", borderLeft: "3px solid var(--accent)" }}>
        <div>Calculation: {record.normalized_quantity ?? "0"} {record.normalized_unit} × Base Factor → {record.estimated_kg_co2e ?? "-"} kgCO2e</div>
        <small style={{ color: "var(--muted)", display: "block", marginTop: "6px" }}>
          Source Tracking: Scope mapped automatically via {record.source.kind} payload parameters.
        </small>
      </div>
      <h3>Flags</h3>
      <div className="flag-list">{record.flags.length ? record.flags.map((flag) => <Badge key={flag} tone="flag">{flag}</Badge>) : "No flags"}</div>
      <h3>Raw source payload</h3>
      <pre>{JSON.stringify(record.raw_record?.raw_payload, null, 2)}</pre>
      <h3>Audit events</h3>
      <ol className="events">
        {record.events.map((event) => <li key={event.id}><strong>{event.event_type}</strong><span>{new Date(event.created_at).toLocaleString()}</span><p>{event.note}</p></li>)}
      </ol>
    </section>
  );
}

function BatchList({ batches }) {
  return (
    <section className="batch-list">
      <h2>Recent batches</h2>
      {batches.slice(0, 6).map((batch) => (
        <div className="batch" key={batch.id}>
          <strong>{batch.source.kind}</strong>
          <span>{batch.original_filename}</span>
          <small>{batch.imported_count} imported / {batch.failed_count} failed / {batch.suspicious_count} flagged</small>
        </div>
      ))}
    </section>
  );
}

function Badge({ children, tone }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

createRoot(document.getElementById("root")).render(<App />);
