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

const API_BASE = "http://localhost:8000";

function App() {
  const [latest, setLatest] = useState(null);
  const [snapshots, setSnapshots] = useState([]);

  async function fetchData() {
    const latestRes = await fetch(`${API_BASE}/latest`);
    const snapshotsRes = await fetch(`${API_BASE}/snapshots?limit=50`);

    setLatest(await latestRes.json());
    setSnapshots(await snapshotsRes.json());
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!latest) {
    return <div className="page">Loading...</div>;
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Smart Grid Dashboard</h1>
          <p>Live energy demand, solar input and grid pricing</p>
        </div>
        <div className="status">Tick {latest.tick}</div>
      </header>

      <section className="hero">
        <div>
          <p className="label">Current Demand</p>
          <h2>{latest.instant_demand.toFixed(2)} W</h2>
          <p>Live domestic emulator load</p>
        </div>
      </section>

      <section className="cards">
        <StatCard title="Sun" value={`${latest.sun.toFixed(0)}%`} />
        <StatCard title="Buy Price" value={`${latest.buy_price.toFixed(0)}`} />
        <StatCard title="Sell Price" value={`${latest.sell_price.toFixed(0)}`} />
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
    </div>
  );
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