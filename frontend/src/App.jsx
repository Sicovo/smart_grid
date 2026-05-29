import { useEffect, useState } from "react";
import {
  Line,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from "recharts";
import SmpsModules from "./SmpsModules";
import "./App.css";
import SMPS from "./SMPS";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  "/api";

const MODULE_ROLES = ["pv", "grid", "export", "cap", "led", "lux"];
const STALE_AFTER_MS = 5000;

function getModuleStatus(module) {
  if (!module) return "offline";

  const t = new Date(module.timestamp).getTime();
  if (!Number.isFinite(t)) return "offline";

  if (Date.now() - t > STALE_AFTER_MS) return "stale";
  if (module.trip) return "trip";
  if (module.wd) return "watchdog";
  if (module.role !== "lux" && !module.enable) return "disabled";

  return "online";
}

function StatusDot({ status }) {
  return <span className={`module-status-dot module-status-${status}`} />;
}

function App() {
  const [activeView, setActiveView] = useState("energy");
  const [latest, setLatest] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [modules, setModules] = useState({});

  async function fetchData() {
    try {
      const [latestRes, snapshotsRes, modulesRes] = await Promise.all([
        fetch(`${API_BASE}/latest`),
        fetch(`${API_BASE}/snapshots?limit=50`),
        fetch(`${API_BASE}/modules/latest`),
      ]);

      if (!latestRes.ok || !snapshotsRes.ok) {
        throw new Error("Backend API request failed");
      }

      const [latestData, snapshotsData] = await Promise.all([
        latestRes.json(),
        snapshotsRes.json(),
      ]);

      const modulesData = modulesRes.ok ? await modulesRes.json() : {};

      setLatest(latestData?.error ? null : latestData);
      setSnapshots(Array.isArray(snapshotsData) ? snapshotsData : []);
      setModules(modulesData || {});
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
      setLatest(null);
      setSnapshots([]);
      setModules({});
    }
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <button
            className="topbar-logo"
            onClick={() => setActiveView("energy")}
            aria-label="Home"
          >
            <img
              src="/oct.png"
              alt="Octopus"
              className="topbar-logo-img"
            />
          </button>
          <nav className="topbar-nav">
            <button className="topbar-link">Energy</button>
            <button className="topbar-link">Heat pumps</button>
            <button className="topbar-link">Solar & battery</button>
            <button className="topbar-link">Electric vehicles</button>
          </nav>

          <div className="topbar-spacer" />

          <button className="topbar-link topbar-support">Support</button>
          <div className="topbar-user">
            <span>Watt's Up</span>
            <span className="topbar-avatar">F</span>
          </div>
        </div>
      </header>

      <div className="app-layout">
        <aside className="sidebar">
          <div
            className={`nav-item ${activeView === "energy" ? "active" : ""}`}
            onClick={() => setActiveView("energy")}
          >
            <span className="nav-icon">🏠</span>
            <span>Home</span>
          </div>
          <div
            className={`nav-item ${activeView === "smps-overview" ? "active" : ""}`}
            onClick={() => setActiveView("smps-overview")}
          >
            <span className="nav-icon">📈</span>
            <span>SMPS Overview</span>
          </div>
          <div
            className={`nav-item ${activeView === "smps" ? "active" : ""}`}
            onClick={() => setActiveView("smps")}
          >
            <span className="nav-icon">🔌</span>
            <span>SMPS Modules</span>
          </div>
          <div className="nav-item">
            <span className="nav-icon">⚡</span>
            <span>My Energy</span>
          </div>
          <div className="nav-item">
            <span className="nav-icon">💳</span>
            <span>Payments</span>
          </div>
          <div className="nav-item">
            <span className="nav-icon">🐙</span>
            <span>Octoplus</span>
          </div>
        </aside>

        <main className="main-content">
        {activeView === "smps" ? (
          <div className="dashboard-container" style={{ maxWidth: "100%" }}>
            <h1 className="page-title">SMPS Modules</h1>
            <p className="date-subtitle">
              Live telemetry from backend DB. Commands are sent directly to each module&apos;s HTTP server.
            </p>
            <SmpsModules apiBase={API_BASE} />
          </div>
        ) : activeView === "smps-overview" ? (
          <div className="dashboard-container" style={{ maxWidth: "100%" }}>
            <h1 className="page-title">SMPS Overview</h1>
            <p className="date-subtitle">
              Module telemetry plots from backend DB.
            </p>
            <SMPS apiBase={API_BASE} />
          </div>
        ) : (
          <div className="dashboard-container">
            <h1 className="page-title">My energy insights</h1>

            <div className="tabs-container">
              <div className="tab active">Day</div>
              <div className="tab">Week</div>
              <div className="tab">Month</div>
              <div className="tab">Year</div>
              <div className="tab">Custom</div>
            </div>

            <p className="date-subtitle">Latest Tick: {latest?.tick ?? "..."}</p>

            <section className="card">
              <div className="card-header">
                <span className="icon-green">●</span> Module Status
              </div>

              <div className="module-status-grid">
                {MODULE_ROLES.map((role) => {
                  const status = getModuleStatus(modules?.[role]);
                  return (
                    <div key={role} className="module-status-item">
                      <div className="module-status-left">
                        <StatusDot status={status} />
                        <span className="module-status-role">{role.toUpperCase()}</span>
                      </div>
                      <span className={`module-status-label module-status-text-${status}`}>
                        {status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <span className="icon-cyan">✦</span> Grid State
              </div>

              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={snapshots}>
                    <XAxis
                      dataKey="tick"
                      stroke="#a69ec4"
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#14052e",
                        borderColor: "#27134d",
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: "#00f0ff" }}
                    />
                    <Bar
                      dataKey="instant_demand"
                      name="Demand (W)"
                      fill="#00f0ff"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={snapshots}>
                    <XAxis
                      dataKey="tick"
                      stroke="#a69ec4"
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#14052e",
                        borderColor: "#27134d",
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: "#ffc800" }}
                    />
                    <Bar
                      dataKey="sun"
                      name="Solar Input"
                      fill="#ffc800"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="stats-row">
                <div className="stat-box">
                  <p>Current Demand</p>
                  <h3>
                    {typeof latest?.instant_demand === "number"
                      ? `${latest.instant_demand.toFixed(2)} W`
                      : "-"}
                  </h3>
                </div>
                <div className="stat-box">
                  <p>Solar Input</p>
                  <h3>
                    {typeof latest?.sun === "number"
                      ? `${latest.sun.toFixed(0)}%`
                      : "-"}
                  </h3>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <span className="icon-orange">⚡</span> Deferrable Loads
              </div>

              {latest?.deferables?.length ? (
                latest.deferables.map((job, idx) => {
                  const now = latest.tick;
                  const totalWindow = job.end - job.start;
                  const elapsed = Math.min(Math.max(now - job.start, 0), totalWindow);
                  const progress = totalWindow > 0 ? (elapsed / totalWindow) * 100 : 0;
                  const remaining = Math.max(job.end - now, 0);
                  const expired = now > job.end;
                  const notStarted = now < job.start;

                  return (
                    <div
                      key={idx}
                      className={`deferable-job ${expired ? "expired" : ""}`}
                    >
                      <div className="job-header">
                        <span>Job {idx + 1}</span>
                        <span>{Number(job.energy).toFixed(1)} J</span>
                      </div>

                      <div className="job-meta">
                        tick {job.start} → {job.end} ·{" "}
                        {expired
                          ? "expired"
                          : notStarted
                            ? `starts in ${job.start - now} ticks`
                            : `${remaining} ticks left`}
                      </div>

                      <div className="progress-bg">
                        <div
                          className="progress-fill"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p>No deferrable loads</p>
              )}
            </section>

            <section className="two-col">
              <div className="insight-card">
                <div className="sub">Current Market...</div>
                <div className="val icon-cyan">
                  {typeof latest?.buy_price === "number"
                    ? latest.buy_price.toFixed(0)
                    : "-"}
                </div>
                <div>Buy Price (pence/kWh)</div>
                <p style={{ fontSize: 12, color: "#a69ec4", marginTop: 12 }}>
                  Grid import price for this current tick.
                </p>
              </div>

              <div className="insight-card tree-bg">
                <div className="sub">Exporting power...</div>
                <div className="val icon-green">
                  {typeof latest?.sell_price === "number"
                    ? latest.sell_price.toFixed(0)
                    : "-"}
                </div>
                <div>Sell Price (pence/kWh)</div>
                <p
                  style={{
                    fontSize: 12,
                    color: "#a69ec4",
                    marginTop: 12,
                    position: "relative",
                    zIndex: 2,
                  }}
                >
                  Earnings if feeding back to grid.
                </p>
              </div>
            </section>

            <section className="card">
              <h2>Get your geek on</h2>
              <p style={{ color: "#a69ec4", marginBottom: 20 }}>
                Backend snapshot dataset from the local DB.
              </p>
              <div
                style={{
                  padding: "12px",
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: "8px",
                  color: "#00f0ff",
                }}
              >
                ✦ {snapshots.length} data points loaded
              </div>
              <button className="btn-pink" onClick={() => console.log(snapshots)}>
                Log smart data
              </button>
            </section>
          </div>
        )}
        </main>
      </div>
    </div>
  );
}

export default App;