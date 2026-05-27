import { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";

const ROLES = ["pv", "grid", "export", "cap", "led"];
const HIST_MAX = 60;
const STALE_AFTER_MS = 5000;

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

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`${apiBase}/modules/latest`);
        if (!res.ok) return;

        const data = await res.json();
        if (cancelled) return;

        setModules(data || {});

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

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [apiBase]);

  return (
    <div className="smps-plots-page">
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