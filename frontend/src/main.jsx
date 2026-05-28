import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Check, Database, FileUp, Filter, Lock, RefreshCw, Search, ShieldCheck, TriangleAlert, X } from "lucide-react";
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

  const query = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    return params.toString();
  }, [filters]);

  async function refresh() {
    const [summaryRes, recordsRes, batchesRes] = await Promise.all([
      fetch(`${API_BASE}/summary/`),
      fetch(`${API_BASE}/activities/${query ? `?${query}` : ""}`),
      fetch(`${API_BASE}/batches/`),
    ]);
    setSummary(await summaryRes.json());
    setRecords(await recordsRes.json());
    setBatches(await batchesRes.json());
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
      <header className="topbar">
        <div>
          <p className="eyebrow">Breathe ESG</p>
          <h1>Ingestion Review</h1>
        </div>
        <button className="icon-button" onClick={refresh} title="Refresh dashboard">
          <RefreshCw size={18} />
        </button>
      </header>

      <main className="workspace">
        <section className="left-pane">
          <Stats summary={summary} />
          <ImportPanel busy={busy} upload={upload} importConcur={importConcur} seed={seed} message={message} />
          <FilterBar filters={filters} setFilters={setFilters} />
          <RecordTable records={records} selected={selected} setSelected={setSelected} />
        </section>
        <aside className="right-pane">
          <DetailPanel record={selected} review={review} />
          <BatchList batches={batches} />
        </aside>
      </main>
    </div>
  );
}

function Stats({ summary }) {
  const items = [
    ["Total", summary?.total ?? 0, Database],
    ["Pending", summary?.pending ?? 0, Filter],
    ["Suspicious", summary?.suspicious ?? 0, TriangleAlert],
    ["Approved", summary?.approved ?? 0, ShieldCheck],
    ["Locked", summary?.locked ?? 0, Lock],
    ["Failed", summary?.failed ?? 0, X],
  ];
  return (
    <section className="stats-grid">
      {items.map(([label, value, Icon]) => (
        <div className="stat" key={label}>
          <Icon size={18} />
          <span>{label}</span>
          <strong>{value}</strong>
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

function RecordTable({ records, selected, setSelected }) {
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
