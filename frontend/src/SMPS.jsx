import { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const ROLES = ["pv", "grid", "export", "cap", "led"];
const HIST_MAX = 60;
const OVERVIEW_LIMIT = 60;
const STALE_AFTER_MS = 5000;
const TICK_SECONDS = 5;

const ROLE_LABELS = {
  pv: "PV",
  grid: "Grid",
  export: "Export",
  cap: "Capacitor",
  led: "LED Load",
};

const ROLE_COLORS = {
  pv: "#00e676",
  grid: "#00f0ff",
  export: "#b67ad9",
  cap: "#5ec9c0",
  led: "#ff9100",
};

const ROLE_LINES = {
  pv: [
    { key: "v_panel", name: "Vpv", color: "#00e676" },
    { key: "vb_bus", name: "Vbus", color: "#00f0ff" },
    { key: "p_panel", name: "Ppv", color: "#ffc800" },
  ],
  grid: [
    { key: "vb_bus", name: "Vbus", color: "#00f0ff" },
    { key: "v_psu", name: "Vpsu", color: "#ffc800" },
    { key: "p_import", name: "P import", color: "#ff9100" },
  ],
  export: [
    { key: "vb_bus", name: "Vbus", color: "#00f0ff" },
    { key: "v_resistor", name: "Vres", color: "#b67ad9" },
    { key: "p_dissip", name: "P dissip", color: "#ff4d6d" },
  ],
  cap: [
    { key: "v_cap", name: "Vcap", color: "#5ec9c0" },
    { key: "vb_bus", name: "Vbus", color: "#00f0ff" },
    { key: "p_cap", name: "Pcap", color: "#ffc800" },
  ],
  led: [
    { key: "p_red", name: "Red", color: "#ff4d6d" },
    { key: "p_yel", name: "Yellow", color: "#ffc800" },
    { key: "p_grn", name: "Green", color: "#00e676" },
  ],
};

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

function fmt(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (typeof v === "number") return v.toFixed(digits);
  return String(v);
}

function StatusBadge({ status }) {
  return (
    <span className={`module-status-label module-status-text-${status}`}>
      <span className={`module-status-dot module-status-${status}`} />
      {status}
    </span>
  );
}

function toNumber(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function getJobWindow(job) {
  const start = Number(job?.tick_start ?? job?.start);
  const end = Number(job?.tick_end ?? job?.end);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  return { start, end };
}

function getDeferrableDemand(snapshot) {
  const tick = Number(snapshot?.tick);
  if (!Number.isFinite(tick)) return 0;

  const jobs = Array.isArray(snapshot?.deferables) ? snapshot.deferables : [];
  return jobs.reduce((sum, job) => {
    const window = getJobWindow(job);
    if (!window) return sum;
    if (tick < window.start || tick > window.end) return sum;
    return sum + Math.max(0, toNumber(job?.energy));
  }, 0);
}

function getDeferrableSeriesValue(snapshot, index) {
  const tick = Number(snapshot?.tick);
  if (!Number.isFinite(tick)) return 0;

  const jobs = Array.isArray(snapshot?.deferables) ? snapshot.deferables : [];
  const job = jobs[index];
  if (!job) return 0;

  const window = getJobWindow(job);
  if (!window) return 0;
  if (tick < window.start || tick > window.end) return 0;
  return Math.max(0, toNumber(job?.energy));
}

function buildOverviewSeries(gridSnapshots, pvHistory, gridHistory, exportHistory) {
  const pvByTick = new Map();
  const gridByTick = new Map();
  const exportByTick = new Map();

  pvHistory.forEach((row) => {
    const tick = Number(row?.web_tick);
    if (Number.isFinite(tick)) pvByTick.set(tick, row);
  });
  gridHistory.forEach((row) => {
    const tick = Number(row?.web_tick);
    if (Number.isFinite(tick)) gridByTick.set(tick, row);
  });
  exportHistory.forEach((row) => {
    const tick = Number(row?.web_tick);
    if (Number.isFinite(tick)) exportByTick.set(tick, row);
  });

  let cumulativeImportJ = 0;
  let cumulativeExportJ = 0;

  return gridSnapshots.map((snapshot) => {
    const tick = Number(snapshot?.tick);
    const pvRow = pvByTick.get(tick);
    const gridRow = gridByTick.get(tick);
    const exportRow = exportByTick.get(tick);

    const importPower = Math.max(0, toNumber(gridRow?.p_import));
    const exportPower = Math.max(0, toNumber(exportRow?.p_dissip));
    cumulativeImportJ += importPower * TICK_SECONDS;
    cumulativeExportJ += exportPower * TICK_SECONDS;

    return {
      tick,
      pv_power_W: Math.max(0, toNumber(pvRow?.p_panel)),
      instant_demand_W: Math.max(0, toNumber(snapshot?.instant_demand)),
      total_deferrable_J: getDeferrableDemand(snapshot),
      deferrable_1_J: getDeferrableSeriesValue(snapshot, 0),
      deferrable_2_J: getDeferrableSeriesValue(snapshot, 1),
      deferrable_3_J: getDeferrableSeriesValue(snapshot, 2),
      cumulative_import_J: cumulativeImportJ,
      cumulative_export_J: cumulativeExportJ,
    };
  });
}

function OverviewGraphCard({ data }) {
  const latest = data[data.length - 1];

  return (
    <section className="card smps-plot-card smps-overview-card smps-overview-graph-card">
      <div className="smps-plot-header">
        <div>
          <div className="smps-plot-title" style={{ color: "#00f0ff" }}>
            System Dispatch Overview
          </div>
          <div className="smps-plot-sub">
            PV, demand, three deferrable demands, and cumulative grid energy versus tick.
          </div>
        </div>
      </div>

      <div className="smps-plot-stats smps-overview-stats">
        <div className="smps-plot-stat">
          <p>PV Power</p>
          <h3>{latest ? `${fmt(latest.pv_power_W)} W` : "—"}</h3>
        </div>
        <div className="smps-plot-stat">
          <p>Demand</p>
          <h3>{latest ? `${fmt(latest.instant_demand_W)} W` : "—"}</h3>
        </div>
        <div className="smps-plot-stat">
          <p>Total Deferrable</p>
          <h3>{latest ? `${fmt(latest.total_deferrable_J)} J` : "—"}</h3>
        </div>
        <div className="smps-plot-stat">
          <p>Import / Export</p>
          <h3>{latest ? `${fmt(latest.cumulative_import_J, 0)} / ${fmt(latest.cumulative_export_J, 0)} J` : "—"}</h3>
        </div>
      </div>

      <div className="smps-plot-wrapper">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <XAxis
              dataKey="tick"
              stroke="#a69ec4"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              yAxisId="power"
              stroke="#a69ec4"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <YAxis
              yAxisId="energy"
              orientation="right"
              stroke="#a69ec4"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={56}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#14052e",
                borderColor: "#27134d",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#ffffff" }}
            />
            <Legend wrapperStyle={{ color: "#a69ec4", fontSize: 12 }} />
            <Line yAxisId="power" type="monotone" dataKey="pv_power_W" name="PV power" stroke="#00e676" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="power" type="monotone" dataKey="instant_demand_W" name="Demand" stroke="#00f0ff" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="power" type="monotone" dataKey="deferrable_1_J" name="Deferrable 1" stroke="#ffc800" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="power" type="monotone" dataKey="deferrable_2_J" name="Deferrable 2" stroke="#ff9100" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="power" type="monotone" dataKey="deferrable_3_J" name="Deferrable 3" stroke="#5ec9c0" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="energy" type="monotone" dataKey="cumulative_export_J" name="Cumulative export" stroke="#ff4d6d" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="energy" type="monotone" dataKey="cumulative_import_J" name="Cumulative import" stroke="#b67ad9" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function NaiveDispatchCard({
  naive,
  applyBusy,
  applyMsg,
  onApply,
  showHostConfig,
  onToggleHostConfig,
  backendHosts,
  onHostsChange,
  onSaveHosts,
  hostsMsg,
  autoApply,
  onAutoApplyChange,
  cooldownSec,
  onCooldownChange,
}) {
  return (
    <section className="card smps-plot-card smps-overview-card">
      <div className="card-header">
        <span className="icon-green">●</span> Naive Dispatch
      </div>

      <div className="naive-grid naive-grid-compact">
        <div className="naive-item">
          <p>PV Power</p>
          <h3>{typeof naive?.inputs?.pv_power_W === "number" ? `${naive.inputs.pv_power_W.toFixed(2)} W` : "-"}</h3>
        </div>
        <div className="naive-item">
          <p>Demand</p>
          <h3>{typeof naive?.inputs?.demand_W === "number" ? `${naive.inputs.demand_W.toFixed(2)} W` : "-"}</h3>
        </div>
        <div className="naive-item">
          <p>Cap i_cmd</p>
          <h3>{typeof naive?.suggested?.cap?.i_cmd === "number" ? `${naive.suggested.cap.i_cmd.toFixed(3)} A` : "-"}</h3>
        </div>
        <div className="naive-item">
          <p>LED each</p>
          <h3>{typeof naive?.suggested?.led?.p_red === "number" ? `${naive.suggested.led.p_red.toFixed(2)} W` : "-"}</h3>
        </div>
      </div>

      <p className="naive-meta">
        Served deferables: {Array.isArray(naive?.served_deferrables) ? naive.served_deferrables.length : 0}
        {" · "}
        Remaining surplus: {typeof naive?.remaining_surplus_W === "number" ? `${naive.remaining_surplus_W.toFixed(2)} W` : "-"}
      </p>

      <div className="naive-toolbar">
        <label className="naive-auto-label">
          <input
            type="checkbox"
            checked={autoApply}
            onChange={(e) => onAutoApplyChange(e.target.checked)}
          />
          Auto apply
        </label>

        <label className="naive-auto-label">
          Cooldown
          <input
            className="naive-cooldown-input"
            type="number"
            min="1"
            step="1"
            value={cooldownSec}
            onChange={(e) => onCooldownChange(Number(e.target.value) || 1)}
          />
          s
        </label>

        <button className="naive-host-toggle" onClick={onToggleHostConfig}>
          {showHostConfig ? "Hide backend hosts" : "Edit backend hosts"}
        </button>
      </div>

      {showHostConfig && (
        <div className="naive-host-panel">
          <div className="naive-host-grid">
            <label>
              cap
              <input
                value={backendHosts.cap}
                onChange={(e) => onHostsChange({ ...backendHosts, cap: e.target.value })}
                placeholder="http://192.168.137.23"
              />
            </label>
            <label>
              led
              <input
                value={backendHosts.led}
                onChange={(e) => onHostsChange({ ...backendHosts, led: e.target.value })}
                placeholder="http://192.168.137.24"
              />
            </label>
          </div>
          <div className="naive-host-actions">
            <button className="naive-host-save" onClick={onSaveHosts}>Save backend hosts</button>
            {hostsMsg && <span className="naive-host-msg">{hostsMsg}</span>}
          </div>
        </div>
      )}

      <button className="btn-pink" onClick={() => onApply()} disabled={applyBusy || !naive}>
        {applyBusy ? "Applying..." : "Apply to cap + led modules"}
      </button>

      {applyMsg && <p className="naive-apply-msg">{applyMsg}</p>}
    </section>
  );
}

function ModulePlotCard({ role, data, history }) {
  const status = getModuleStatus(data);
  const lines = ROLE_LINES[role] || [];
  const color = ROLE_COLORS[role];

  const latestStats = {
    pv: [
      ["Vpv", data?.v_panel, "V"],
      ["Vbus", data?.vb_bus, "V"],
      ["Ppv", data?.p_panel, "W"],
    ],
    grid: [
      ["Vbus", data?.vb_bus, "V"],
      ["Vpsu", data?.v_psu, "V"],
      ["Import", data?.p_import, "W"],
    ],
    export: [
      ["Vbus", data?.vb_bus, "V"],
      ["Vres", data?.v_resistor, "V"],
      ["Dissip", data?.p_dissip, "W"],
    ],
    cap: [
      ["Vcap", data?.v_cap, "V"],
      ["SoC", data?.soc_pct, "%"],
      ["Energy", data?.energy_J, "J"],
    ],
    led: [
      ["Red", data?.p_red, "W"],
      ["Yellow", data?.p_yel, "W"],
      ["Green", data?.p_grn, "W"],
    ],
  }[role];

  return (
    <section className="card smps-plot-card">
      <div className="smps-plot-header">
        <div>
          <div className="smps-plot-title" style={{ color }}>
            {ROLE_LABELS[role]}
          </div>
          <div className="smps-plot-sub">
            {data?.timestamp
              ? `Last update: ${new Date(data.timestamp).toLocaleTimeString()}`
              : "No telemetry yet"}
          </div>
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="smps-plot-stats">
        {latestStats.map(([label, value, unit]) => (
          <div className="smps-plot-stat" key={label}>
            <p>{label}</p>
            <h3>
              {fmt(value)}
              <span>{unit}</span>
            </h3>
          </div>
        ))}
      </div>

      <div className="smps-plot-wrapper">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={history}>
            <XAxis
              dataKey="id"
              hide
            />
            <YAxis
              stroke="#a69ec4"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#14052e",
                borderColor: "#27134d",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#ffffff" }}
            />
            {lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="smps-plot-legend">
        {lines.map((line) => (
          <span key={line.key}>
            <i style={{ background: line.color }} />
            {line.name}
          </span>
        ))}
      </div>
    </section>
  );
}

export default function SmpsModules({ apiBase }) {
  const [modules, setModules] = useState({});
  const histRef = useRef(Object.fromEntries(ROLES.map((r) => [r, []])));
  const [hist, setHist] = useState(Object.fromEntries(ROLES.map((r) => [r, []])));
  const [overviewData, setOverviewData] = useState([]);
  const [naive, setNaive] = useState(null);
  const [applyBusy, setApplyBusy] = useState(false);
  const [applyMsg, setApplyMsg] = useState("");
  const [showHostConfig, setShowHostConfig] = useState(false);
  const [backendHosts, setBackendHosts] = useState({ cap: "", led: "" });
  const [hostsMsg, setHostsMsg] = useState("");
  const [autoApply, setAutoApply] = useState(false);
  const [cooldownSec, setCooldownSec] = useState(5);
  const lastAutoApplyRef = useRef(0);

  async function applyNaiveNow(opts = {}) {
    const { silent = false } = opts;

    if (applyBusy) return false;

    setApplyBusy(true);
    if (!silent) setApplyMsg("");

    try {
      const res = await fetch(`${apiBase}/algo/naive/apply`, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Apply request failed: ${res.status}`);
      }

      const data = await res.json();
      if (data?.recommendation) {
        setNaive(data.recommendation);
      }

      if (!silent) {
        const capState = data?.applied?.cap?.ok ? "cap ok" : "cap failed";
        const ledState = data?.applied?.led?.ok ? "led ok" : "led failed";
        setApplyMsg(`${capState}, ${ledState}`);
      }
      return true;
    } catch (err) {
      console.error("Failed to apply naive command", err);
      if (!silent) setApplyMsg("apply failed");
      return false;
    } finally {
      setApplyBusy(false);
    }
  }

  async function loadBackendHosts() {
    try {
      const res = await fetch(`${apiBase}/algo/module-hosts`);
      if (!res.ok) return;
      const data = await res.json();
      const hosts = data?.hosts || {};
      setBackendHosts({ cap: hosts.cap || "", led: hosts.led || "" });
    } catch (err) {
      console.error("Failed to load backend hosts", err);
    }
  }

  async function saveBackendHosts() {
    setHostsMsg("");
    try {
      const res = await fetch(`${apiBase}/algo/module-hosts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hosts: backendHosts }),
      });
      if (!res.ok) {
        throw new Error(`save failed ${res.status}`);
      }
      setHostsMsg("hosts saved");
    } catch (err) {
      console.error("Failed to save backend hosts", err);
      setHostsMsg("save failed");
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const [modulesRes, snapshotsRes, pvRes, gridRes, exportRes, naiveRes] = await Promise.all([
          fetch(`${apiBase}/modules/latest`),
          fetch(`${apiBase}/snapshots?limit=${OVERVIEW_LIMIT}`),
          fetch(`${apiBase}/modules/snapshots/pv?limit=${OVERVIEW_LIMIT}`),
          fetch(`${apiBase}/modules/snapshots/grid?limit=${OVERVIEW_LIMIT}`),
          fetch(`${apiBase}/modules/snapshots/export?limit=${OVERVIEW_LIMIT}`),
          fetch(`${apiBase}/algo/naive`),
        ]);
        if (!modulesRes.ok) return;

        const [data, snapshotsData, pvData, gridData, exportData, naiveData] = await Promise.all([
          modulesRes.json(),
          snapshotsRes.ok ? snapshotsRes.json() : [],
          pvRes.ok ? pvRes.json() : [],
          gridRes.ok ? gridRes.json() : [],
          exportRes.ok ? exportRes.json() : [],
          naiveRes.ok ? naiveRes.json() : null,
        ]);
        if (cancelled) return;

        setModules(data || {});
        setOverviewData(buildOverviewSeries(
          Array.isArray(snapshotsData) ? snapshotsData : [],
          Array.isArray(pvData) ? pvData : [],
          Array.isArray(gridData) ? gridData : [],
          Array.isArray(exportData) ? exportData : [],
        ));
        setNaive(naiveData && !naiveData.error ? naiveData : null);

        ROLES.forEach((role) => {
          const row = data?.[role];
          if (!row) return;

          const h = histRef.current[role];
          h.push(row);
          if (h.length > HIST_MAX) h.shift();
        });

        setHist(Object.fromEntries(
          ROLES.map((role) => [role, [...histRef.current[role]]])
        ));
      } catch (err) {
        console.error("Failed to fetch module telemetry", err);
      }
    }

    loadBackendHosts();
    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [apiBase]);

  useEffect(() => {
    if (!autoApply) return;

    const id = setInterval(() => {
      if (!naive || applyBusy) return;

      const cooldownMs = Math.max(1, Number(cooldownSec) || 1) * 1000;
      const now = Date.now();
      if (now - lastAutoApplyRef.current < cooldownMs) return;

      lastAutoApplyRef.current = now;
      applyNaiveNow({ silent: true });
    }, 1000);

    return () => clearInterval(id);
  }, [autoApply, cooldownSec, naive, applyBusy]);

  return (
    <div className="smps-plots-page">
      <OverviewGraphCard data={overviewData} />
      <NaiveDispatchCard
        apiBase={apiBase}
        naive={naive}
        applyBusy={applyBusy}
        applyMsg={applyMsg}
        onApply={applyNaiveNow}
        showHostConfig={showHostConfig}
        onToggleHostConfig={() => setShowHostConfig((v) => !v)}
        backendHosts={backendHosts}
        onHostsChange={setBackendHosts}
        onSaveHosts={saveBackendHosts}
        hostsMsg={hostsMsg}
        autoApply={autoApply}
        onAutoApplyChange={setAutoApply}
        cooldownSec={cooldownSec}
        onCooldownChange={setCooldownSec}
      />
      {ROLES.map((role) => (
        <ModulePlotCard
          key={role}
          role={role}
          data={modules?.[role]}
          history={hist[role]}
        />
      ))}
    </div>
  );
}