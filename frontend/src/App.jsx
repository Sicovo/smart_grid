import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar
} from "recharts";
import SmpsModules from "./SmpsModules";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  "/api";

const PICO_API_BASE =
  import.meta.env.VITE_PICO_API_BASE_URL ??
  "http://192.168.4.1:8000";

function App() {
  const [activeView, setActiveView] = useState('energy');
  const [latest, setLatest] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [smpsLatest, setSmpsLatest] = useState(null);
  const [smpsSnapshots, setSmpsSnapshots] = useState([]);
  const [smpsSource, setSmpsSource] = useState("backend");
  const [picoRefreshing, setPicoRefreshing] = useState(false);
  const [picoError, setPicoError] = useState(null);

  async function fetchPicoSmps() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    try {
      const [smpsLatestRes, smpsSnapshotsRes] = await Promise.all([
        fetch(`${PICO_API_BASE}/smps/latest`, { signal: controller.signal }),
        fetch(`${PICO_API_BASE}/smps/snapshots?limit=120`, { signal: controller.signal }),
      ]);

      if (!smpsLatestRes.ok || !smpsSnapshotsRes.ok) {
        throw new Error("Pico API request failed");
      }

      const [smpsLatestData, smpsSnapshotsData] = await Promise.all([
        smpsLatestRes.json(),
        smpsSnapshotsRes.json(),
      ]);

      return { smpsLatestData, smpsSnapshotsData };
    } finally {
      clearTimeout(timeout);
    }
  }

  async function fetchData() {
    try {
      const [latestRes, snapshotsRes] = await Promise.all([
        fetch(`${API_BASE}/latest`),
        fetch(`${API_BASE}/snapshots?limit=50`),
      ]);

      if (!latestRes.ok || !snapshotsRes.ok) {
        throw new Error("Backend API request failed");
      }

      const [latestData, snapshotsData] = await Promise.all([
        latestRes.json(),
        snapshotsRes.json(),
      ]);

      let smpsLatestData = null;
      let smpsSnapshotsData = [];
      let source = "pico";

      try {
        const picoResult = await fetchPicoSmps();
        smpsLatestData = picoResult.smpsLatestData;
        smpsSnapshotsData = picoResult.smpsSnapshotsData;
      } catch (_err) {
        source = "backend";
        const [smpsLatestRes, smpsSnapshotsRes] = await Promise.all([
          fetch(`${API_BASE}/smps/latest`),
          fetch(`${API_BASE}/smps/snapshots?limit=120`),
        ]);

        if (!smpsLatestRes.ok || !smpsSnapshotsRes.ok) {
          throw new Error("Backend SMPS API request failed");
        }

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
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
      setLatest(null);
      setSnapshots([]);
      setSmpsLatest(null);
      setSmpsSnapshots([]);
      setSmpsSource("backend");
    }
  }

  async function refreshPicoNow() {
    setPicoRefreshing(true);
    setPicoError(null);
    try {
      const { smpsLatestData, smpsSnapshotsData } = await fetchPicoSmps();
      setSmpsLatest(smpsLatestData?.error ? null : smpsLatestData);
      setSmpsSnapshots(Array.isArray(smpsSnapshotsData) ? smpsSnapshotsData : []);
      setSmpsSource("pico");
    } catch (err) {
      console.warn("Pico manual refresh failed", err);
      setPicoError("无法直接访问 Pico，已回退到后端数据库");
      setSmpsSource("backend");
    } finally {
      setPicoRefreshing(false);
    }
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      {/* 侧边栏导航 (完美还原截图左侧) */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span>🐙</span> Octopus
        </div>
        <div className={`nav-item ${activeView === 'energy' ? 'active' : ''}`}
             onClick={() => setActiveView('energy')}>⚡ My Energy</div>
        <div className={`nav-item ${activeView === 'smps' ? 'active' : ''}`}
             onClick={() => setActiveView('smps')}>🔌 SMPS Modules</div>
        <div className="nav-item">🏠 Home</div>
        <div className="nav-item">💳 Payments</div>
        <div className="nav-item">🐙 Octopus</div>
      </aside>

      {/* 主面板区 */}
      <main className="main-content">
        {activeView === 'smps' ? (
          <div className="dashboard-container" style={{ maxWidth: '100%' }}>
            <h1 className="page-title">SMPS Modules</h1>
            <p className="date-subtitle">Live telemetry from firmware modules. Commands sent directly to each module's HTTP server.</p>
            <SmpsModules apiBase={API_BASE} />
          </div>
        ) : (
        <div className="dashboard-container">
          
          <h1 className="page-title">My energy insights</h1>

          {/* 顶部分类 Tab */}
          <div className="tabs-container">
            <div className="tab active">Day</div>
            <div className="tab">Week</div>
            <div className="tab">Month</div>
            <div className="tab">Year</div>
            <div className="tab">Custom</div>
          </div>
          <p className="date-subtitle">Latest Tick: {latest?.tick ?? "..."}</p>

          {/* 第一块: Electricity (映射为 Grid State 和 Demand) */}
          <section className="card">
            <div className="card-header">
              <span className="icon-cyan">✦</span> Grid State (Electricity)
            </div>
            
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={snapshots}>
                  <XAxis dataKey="tick" stroke="#a69ec4" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#14052e', borderColor: '#27134d', borderRadius: '8px' }}
                    itemStyle={{ color: '#00f0ff' }}
                  />
                  {/* 使用青色柱状图模拟 Octopus 的耗电图 */}
                  <Bar dataKey="instant_demand" name="Demand (W)" fill="#00f0ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={snapshots}>
                  <XAxis dataKey="tick" stroke="#a69ec4" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#14052e', borderColor: '#27134d', borderRadius: '8px' }}
                    itemStyle={{ color: '#00f0ff' }}
                  />
                  {/* 使用青色柱状图模拟 Octopus 的耗电图 */}
                  <Bar dataKey="sun" name="Solar Input" fill="#ffc800" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="stats-row">
              <div className="stat-box">
                <p>Current Demand</p>
                <h3>{typeof latest?.instant_demand === "number" ? `${latest.instant_demand.toFixed(2)} W` : "-"}</h3>
              </div>
              <div className="stat-box">
                <p>Solar Input (Sun)</p>
                <h3>{typeof latest?.sun === "number" ? `${latest.sun.toFixed(0)}%` : "-"}</h3>
              </div>
            </div>
          </section>

          {/* 第二块: Gas 区域 (映射为 SMPS Live 状态) */}
          <section className="card">
            <div className="card-header">
              <span className="icon-orange">🔥</span> SMPS Data (Gas)
            </div>

            {/* 如果没有SMPS数据，展示经典的 Fiddlesticks 卡片 */}
            {!smpsLatest ? (
              <div className="fiddlesticks">
                <h2>Fiddlesticks!</h2>
                <p>It looks like there aren't any live SMPS readings right now. Waiting for serial data on the backend.</p>
                <button className="btn-pink" onClick={refreshPicoNow} disabled={picoRefreshing}>
                  {picoRefreshing ? 'Refreshing Pico…' : 'Refresh Pico from Pico board'}
                </button>
                {picoError && <p style={{ color: '#ff8e8e', marginTop: 12 }}>{picoError}</p>}
              </div>
            ) : (
              <div className="fiddlesticks">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2>SMPS is Live</h2>
                  <button className="btn-pink" onClick={refreshPicoNow} disabled={picoRefreshing}>
                    {picoRefreshing ? 'Refreshing Pico…' : 'Refresh Pico'}
                  </button>
                </div>
                <p style={{ fontSize: 14, color: '#a69ec4', marginBottom: 14 }}>
                  Showing data from: {smpsSource === 'pico' ? 'Pico board' : 'backend DB'}
                </p>
                <div className="stats-row" style={{ flexWrap: 'wrap' }}>
                  <div className="stat-box" style={{minWidth: '45%'}}><p>Va</p><h3>{formatSmps(smpsLatest?.va)}</h3></div>
                  <div className="stat-box" style={{minWidth: '45%'}}><p>Vb</p><h3>{formatSmps(smpsLatest?.vb)}</h3></div>
                  <div className="stat-box" style={{minWidth: '45%'}}><p>iL</p><h3>{formatSmps(smpsLatest?.iL)}</h3></div>
                  <div className="stat-box" style={{minWidth: '45%'}}><p>Flags</p><h3>{formatFlags(smpsLatest)}</h3></div>
                </div>
              </div>
            )}
          </section>

          {/* 第三块: 洞察 Insights (映射为 Buy / Sell Prices) */}
          <section className="two-col">
            <div className="insight-card">
              <div className="sub">Current Market...</div>
              <div className="val icon-cyan">
                {typeof latest?.buy_price === "number" ? latest.buy_price.toFixed(0) : "-"}
              </div>
              <div>Buy Price (pence/kWh)</div>
              <p style={{fontSize: 12, color: '#a69ec4', marginTop: 12}}>
                Grid import price for this current tick.
              </p>
            </div>
            
            <div className="insight-card tree-bg">
              <div className="sub">Exporting power...</div>
              <div className="val icon-green">
                {typeof latest?.sell_price === "number" ? latest.sell_price.toFixed(0) : "-"}
              </div>
              <div>Sell Price (pence/kWh)</div>
              {/* 装饰性文字模拟原图的树木碳排卡片 */}
              <p style={{fontSize: 12, color: '#a69ec4', marginTop: 12, position: 'relative', zIndex: 2}}>
                Earnings if feeding back to grid.
              </p>
            </div>
          </section>

          {/* 第四块: Get your geek on */}
          <section className="card">
            <h2>Get your geek on</h2>
            <p style={{color: '#a69ec4', marginBottom: 20}}>
              Download your full backend snapshot dataset to analyze offline.
            </p>
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', color: '#00f0ff'}}>
              ✦ 50 Data points recorded
            </div>
            <button className="btn-pink" onClick={() => console.log(snapshots)}>
              Download your smart data
            </button>
          </section>

          {/* 第五块: When you use electricity matters (映射为 SMPS 历史图表) */}
          <section className="card green-card">
            <div className="green-card-header">
              <span className="icon-green">🌿</span> SMPS History until latest tick
            </div>
            <p>
              Monitor the Va, Vb and iL over the last 120 samples. Green sections indicate healthy power conversion.
            </p>
            
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={smpsSnapshots}>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#14052e', borderColor: '#27134d' }}
                  />
                  {/* 使用青色、绿色和品红色渲染线条 */}
                  <Line type="step" dataKey="va" stroke="#00f0ff" strokeWidth={2} dot={false} />
                  <Line type="step" dataKey="vb" stroke="#00e676" strokeWidth={2} dot={false} />
                  <Line type="step" dataKey="iL" stroke="#f721a3" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div style={{marginTop: 16, borderTop: '1px solid #3c267a', paddingTop: 16}}>
              <p style={{color: '#00e676', fontWeight: 'bold'}}>✓ System is active: good time to log data.</p>
            </div>
          </section>

        </div>
        )}
      </main>
    </div>
  );
}

// 格式化辅助函数保持不变
function formatSmps(value) {
  if (typeof value !== "number") return "-";
  return value.toFixed(3);
}

function formatFlags(sample) {
  if (!sample) return "-";
  return `${sample.CL ?? "-"}/${sample.BU ?? "-"}/${sample.OC ?? "-"}`;
}

export default App;