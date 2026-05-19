import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

const PICO_API_BASE =
  import.meta.env.VITE_PICO_API_BASE_URL ??
  "http://192.168.4.1:8000";

function App() {
  const [latest, setLatest] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [smpsLatest, setSmpsLatest] = useState(null);
  const [smpsSnapshots, setSmpsSnapshots] = useState([]);
  const [smpsSource, setSmpsSource] = useState("backend");

  async function fetchData() {
    const [latestRes, snapshotsRes] = await Promise.all([
      fetch(`${API_BASE}/latest`),
      fetch(`${API_BASE}/snapshots?limit=50`),
    ]);

    const [latestData, snapshotsData] = await Promise.all([
      latestRes.json(),
      snapshotsRes.json(),
    ]);

    let smpsLatestData = null;
    let smpsSnapshotsData = [];
    let source = "pico";

    try {
      const [smpsLatestRes, smpsSnapshotsRes] = await Promise.all([
        fetch(`${PICO_API_BASE}/smps/latest`),
        fetch(`${PICO_API_BASE}/smps/snapshots?limit=120`),
      ]);

      [smpsLatestData, smpsSnapshotsData] = await Promise.all([
        smpsLatestRes.json(),
        smpsSnapshotsRes.json(),
      ]);
    } catch (_err) {
      source = "backend";
      const [smpsLatestRes, smpsSnapshotsRes] = await Promise.all([
        fetch(`${API_BASE}/smps/latest`),
        fetch(`${API_BASE}/smps/snapshots?limit=120`),
      ]);

      [smpsLatestData, smpsSnapshotsData] = await Promise.all([
        smpsLatestRes.json(),
        smpsSnapshotsRes.json(),
      ]);
    }

    setLatest(latestData?.error ? null : latestData);
    setSnapshots(Array.isArray(snapshotsData) ? snapshotsData : []);
    setSmpsLatest(smpsLatestData?.error ? null : smpsLatestData);
    setSmpsSnapshots(Array.isArray(smpsSnapshotsData) ? smpsSnapshotsData : []);
    setSmpsSource(source);
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Smart Grid Dashboard</h1>
          <p>Live energy demand, solar input and grid pricing</p>
        </div>
        <div className="status">Tick {latest?.tick ?? "-"}</div>
      </header>

      <section className="hero">
        <div>
          <p className="label">Current Demand</p>
          <h2>{typeof latest?.instant_demand === "number" ? `${latest.instant_demand.toFixed(2)} W` : "-"}</h2>
          <p>Live domestic emulator load</p>
        </div>
      </section>

      <section className="cards">
        <StatCard title="Sun" value={typeof latest?.sun === "number" ? `${latest.sun.toFixed(0)}%` : "-"} />
        <StatCard title="Buy Price" value={typeof latest?.buy_price === "number" ? `${latest.buy_price.toFixed(0)}` : "-"} />
        <StatCard title="Sell Price" value={typeof latest?.sell_price === "number" ? `${latest.sell_price.toFixed(0)}` : "-"} />
        <StatCard title="Data Points" value={snapshots.length} />
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Historic Grid State</h3>
          <p>Last 50 backend snapshots</p>
        </div>

        <div className="chart">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={snapshots}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="tick" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="instant_demand" name="Demand" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="sun" name="Sun" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="buy_price" name="Buy Price" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="sell_price" name="Sell Price" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>SMPS Live</h3>
          <p>{smpsLatest ? `Latest serial sample (${smpsSource})` : "Waiting for SMPS serial data"}</p>
        </div>
        <div className="cards cards-tight">
          <StatCard title="Va" value={formatSmps(smpsLatest?.va)} />
          <StatCard title="Vb" value={formatSmps(smpsLatest?.vb)} />
          <StatCard title="Vpot" value={formatSmps(smpsLatest?.vpot)} />
          <StatCard title="iL" value={formatSmps(smpsLatest?.iL)} />
          <StatCard title="Duty" value={formatInt(smpsLatest?.duty)} />
          <StatCard title="CL / BU / OC" value={formatFlags(smpsLatest)} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>SMPS History</h3>
          <p>Last 120 SMPS samples from backend</p>
        </div>

        <div className="chart">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={smpsSnapshots}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="id" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="va" name="Va" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="vb" name="Vb" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="iL" name="iL" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="i_ref" name="i_ref" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}

function formatSmps(value) {
  if (typeof value !== "number") {
    return "-";
  }
  return value.toFixed(3);
}

function formatInt(value) {
  if (typeof value !== "number") {
    return "-";
  }
  return String(Math.round(value));
}

function formatFlags(sample) {
  if (!sample) {
    return "-";
  }
  return `${sample.CL ?? "-"}/${sample.BU ?? "-"}/${sample.OC ?? "-"}`;
}

function StatCard({ title, value }) {
  return (
    <div className="card">
      <p>{title}</p>
      <h3>{value}</h3>
    </div>
  );
}

export default App;