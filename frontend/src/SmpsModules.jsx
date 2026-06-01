import { useState, useEffect, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";

// ─── Constants ────────────────────────────────────────────────────────────────

const ROLES = ['pv', 'grid', 'export', 'cap', 'led', 'lux'];

const DEFAULT_HOSTS = {
  pv:     'pv.local',
  grid:   'grid.local',
  export: 'export.local',
  cap:    'cap.local',
  led:    'led.local',
  lux:    'lux.local',
};

const ROLE_COLORS = {
  pv:     '#6fb86f',
  grid:   '#5a8ec9',
  export: '#b67ad9',
  cap:    '#5ec9c0',
  led:    '#d9a85a',
  lux:    '#f5c84b',
};

const ROLE_LABELS = {
  pv:     'PV — boost, MPPT',
  grid:   'Grid — buck, CV import',
  export: 'Export — buck, CV dissipate',
  cap:    'Cap — bidirectional, current-cmd',
  led:    'LED — 3× CC driver',
  lux:    'Lux — irradiance sensor',
};

const MOD_CHART_LINES = {
  pv:     [
    { key: 'v_panel', label: 'Vpv',  color: '#6fb86f' },
    { key: 'vb_bus',  label: 'Vbus', color: '#e6e6e6' },
    { key: 'iL',      label: 'iL',   color: '#5a8ec9' },
  ],
  grid:   [
    { key: 'vb_bus', label: 'Vbus', color: '#e6e6e6' },
    { key: 'v_psu',  label: 'Vpsu', color: '#d9a85a' },
    { key: 'iL',     label: 'iL',   color: '#5a8ec9' },
  ],
  export: [
    { key: 'vb_bus',     label: 'Vbus', color: '#e6e6e6' },
    { key: 'v_resistor', label: 'Vres', color: '#6fb86f' },
    { key: 'iL',         label: 'iL',   color: '#b67ad9' },
  ],
  cap:    [
    { key: 'v_cap',  label: 'Vcap', color: '#5ec9c0' },
    { key: 'vb_bus', label: 'Vbus', color: '#e6e6e6' },
    { key: 'iL',     label: 'iL',   color: '#5ec9c0' },
  ],
  lux:    [
    { key: 'v_ldr', label: 'V_ldr', color: '#f5c84b' },
  ],
  led:    [
    { key: 'i_red', label: 'R', color: '#e07070' },
    { key: 'i_yel', label: 'Y', color: '#d9c95a' },
    { key: 'i_grn', label: 'G', color: '#6fb86f' },
  ],
};

const HIST_MAX = 60;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(v, digits = 2) {
  if (v === null || v === undefined || (typeof v === 'number' && isNaN(v))) return '—';
  if (typeof v === 'number') return v.toFixed(digits);
  return String(v);
}

// ─── Shared UI atoms ──────────────────────────────────────────────────────────

function StatusPill({ d, role }) {
  if (!d) return <span className="smps-pill smps-pill-offline">offline</span>;
  if (role === 'lux') {
    return d.calibrated
      ? <span className="smps-pill smps-pill-ok">calibrated</span>
      : <span className="smps-pill smps-pill-warn">uncal</span>;
  }
  if (d.trip)    return <span className="smps-pill smps-pill-err">TRIP</span>;
  if (d.wd)      return <span className="smps-pill smps-pill-warn">watchdog</span>;
  if (!d.enable) return <span className="smps-pill smps-pill-warn">disabled</span>;
  return <span className="smps-pill smps-pill-ok">ok</span>;
}

function Stat({ label, val, unit, digits = 2, wide = false }) {
  const display = fmt(val, digits);
  return (
    <div className={`smps-stat${wide ? ' smps-stat-wide' : ''}`}>
      <div className="smps-stat-label">{label}</div>
      <div className="smps-stat-val">
        {display}
        {unit && <span className="smps-stat-unit"> {unit}</span>}
      </div>
    </div>
  );
}

function Btn({ children, onClick, variant = '' }) {
  return (
    <button
      className={`smps-btn${variant ? ' smps-btn-' + variant : ''}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function CtrlRow({ label, children }) {
  return (
    <div className="smps-ctrl-row">
      <span className="smps-ctrl-label">{label}</span>
      <div className="smps-ctrl-body">{children}</div>
    </div>
  );
}

// ─── Per-module stat blocks ───────────────────────────────────────────────────

function PVStats({ d }) {
  if (!d) return null;
  const irrPct = typeof d.irradiance === 'number' ? d.irradiance * 100 : null;
  return <>
    <Stat label="Vpanel (Vb)" val={d.v_panel}     unit="V" />
    <Stat label="Vbus (Va)"   val={d.vb_bus}      unit="V" />
    <Stat label="Inductor iL" val={d.iL}          unit="A" digits={3} />
    <Stat label="PV power"    val={d.p_panel}     unit="W" />
    <Stat label="Ppv 3s avg"  val={d.p_avg3s}     unit="W" digits={3} />
    <Stat label="i_ref"       val={d.i_ref}       unit="A" digits={3} />
    <Stat label="Vmpp target" val={d.vmpp_target} unit="V" />
    <Stat label="MPPT mode"   val={d.mppt_mode ? d.mppt_mode.toUpperCase() : null} />
    <Stat label="Irradiance"  val={irrPct}        unit="%" digits={0} />
  </>;
}

function GridStats({ d }) {
  if (!d) return null;
  return <>
    <Stat label="Grid PSU Va"  val={d.v_psu}     unit="V" />
    <Stat label="Bus Vb"       val={d.vb_bus}    unit="V" />
    <Stat label="Inductor iL"  val={d.iL}        unit="A" digits={3} />
    <Stat label="Import power" val={d.p_import}  unit="W" />
    <Stat label="Pimp 3s avg"  val={d.p_avg3s}   unit="W" digits={3} />
    <Stat label="i_ref"        val={d.i_ref}     unit="A" digits={3} />
    <Stat label="Bus target"   val={d.vb_target} unit="V" />
  </>;
}

function ExportStats({ d }) {
  if (!d) return null;
  return <>
    <Stat label="Bus Va"        val={d.vb_bus}      unit="V" />
    <Stat label="Load Vb"       val={d.v_resistor}  unit="V" />
    <Stat label="Load iL"       val={d.iL}          unit="A" digits={3} />
    <Stat label="Dissipated P"  val={d.p_dissip}    unit="W" />
    <Stat label="i_ref"         val={d.i_ref}       unit="A" digits={3} />
    <Stat label="Bus target"    val={d.vb_target}   unit="V" />
  </>;
}

function CapStats({ d }) {
  if (!d) return null;
  const soc = typeof d.soc_pct === 'number' ? Math.max(0, Math.min(100, d.soc_pct)) : 0;
  return <>
    <Stat label="Cap Va"     val={d.v_cap}     unit="V" />
    <Stat label="Bus Vb"     val={d.vb_bus}    unit="V" />
    <Stat label="Inductor iL" val={d.iL}       unit="A" digits={3} />
    <Stat label="Cap power"  val={d.p_cap}     unit="W" />
    <Stat label="Pcap 3s avg" val={d.p_avg3s}  unit="W" digits={3} />
    <Stat label="i_cmd"      val={d.i_cmd}     unit="A" digits={3} />
    <Stat label="i_cmd_eff"  val={d.i_cmd_eff} unit="A" digits={3} />
    <div className="smps-stat smps-stat-wide">
      <div className="smps-stat-label">State of Charge</div>
      <div className="smps-stat-val">
        {fmt(d.soc_pct, 0)}<span className="smps-stat-unit"> %</span>
      </div>
      <div className="smps-soc-track">
        <div className="smps-soc-fill" style={{ width: soc + '%' }} />
      </div>
    </div>
    <Stat label="Energy" val={d.energy_J} unit="J" digits={1} />
  </>;
}

function LEDStats({ d }) {
  if (!d) return null;
  const total = (d.p_red || 0) + (d.p_yel || 0) + (d.p_grn || 0);
  return (
    <div className="smps-led-wrap">
      <div className="smps-led-total">
        Total load: <strong>{fmt(total, 2)} W</strong>
      </div>
      <div className="smps-led-table">
        <div className="smps-led-header">
          <span>CH</span><span>I (A)</span><span>V (V)</span><span>P (W)</span>
        </div>
        {['red', 'yel', 'grn'].map(c => (
          <div key={c} className="smps-led-row">
            <span className={`smps-led-color smps-led-${c}`}>{c.toUpperCase()}</span>
            <span>{fmt(d['i_' + c], 3)}</span>
            <span>{fmt(d['v_' + c], 2)}</span>
            <span>{fmt(d['p_' + c], 2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LuxStats({ d }) {
  if (!d) return null;
  const irrPct = typeof d.irradiance === 'number' ? d.irradiance * 100 : null;
  const uncal = !d.calibrated;
  return <>
    {uncal && (
      <div className="smps-stat smps-stat-wide smps-stat-warn">
        <div className="smps-stat-label" style={{ color: '#d9a85a' }}>UNCALIBRATED</div>
        <div style={{ fontSize: 12, color: '#d9a85a', lineHeight: 1.5 }}>
          Lamp OFF → Set 0%. &nbsp; Lamp FULL → Set 100%.
        </div>
      </div>
    )}
    <Stat label="LDR voltage"  val={d.v_ldr}  unit="V" digits={3} />
    <Stat label="Irradiance"   val={irrPct}   unit="%" digits={1} />
    <Stat label="V_dark (cal)" val={d.v_dark} unit="V" digits={3} />
    <Stat label="V_full (cal)" val={d.v_full} unit="V" digits={3} />
  </>;
}

// ─── Per-module control panels ────────────────────────────────────────────────

function PVControls({ d, onCmd }) {
  const [vmpp, setVmpp] = useState('6.23');
  const mode = d?.mppt_mode || '';
  return <>
    <CtrlRow label="MPPT mode">
      <Btn variant={mode === 'fixed' ? 'active' : ''} onClick={() => onCmd({ mppt_mode: 'fixed' })}>Fixed</Btn>
      <Btn variant={mode === 'web'   ? 'active' : ''} onClick={() => onCmd({ mppt_mode: 'web'   })}>Web</Btn>
      <Btn variant={mode === 'po'    ? 'active' : ''} onClick={() => onCmd({ mppt_mode: 'po'    })}>P&amp;O</Btn>
    </CtrlRow>
    <CtrlRow label="Vmpp target">
      <input className="smps-num-input" type="number" value={vmpp} step="0.01" min="3" max="9"
             onChange={e => setVmpp(e.target.value)} />
      <span className="smps-unit-hint">V</span>
      <Btn onClick={() => onCmd({ vmpp_target: parseFloat(vmpp), mppt_mode: 'fixed' })}>Apply (Fixed)</Btn>
    </CtrlRow>
    <div className="smps-quickbar">
      <Btn onClick={() => onCmd({ enable: 1 })}>Enable</Btn>
      <Btn variant="danger" onClick={() => onCmd({ enable: 0 })}>Disable</Btn>
      <Btn variant="warn" onClick={() => onCmd({ reset_trip: 1 })}>⚠ Reset Trip</Btn>
    </div>
  </>;
}

function GridControls({ onCmd }) {
  const [vbt,  setVbt]  = useState('9.5');
  const [imax, setImax] = useState('2.0');
  return <>
    <CtrlRow label="vb_target">
      <input className="smps-num-input" type="number" value={vbt} step="0.05" min="0" max="12"
             onChange={e => setVbt(e.target.value)} />
      <span className="smps-unit-hint">V</span>
      <Btn onClick={() => onCmd({ vb_target: parseFloat(vbt) })}>Apply</Btn>
    </CtrlRow>
    <CtrlRow label="i_ref_max">
      <input className="smps-num-input" type="number" value={imax} step="0.1" min="0" max="2"
             onChange={e => setImax(e.target.value)} />
      <span className="smps-unit-hint">A</span>
      <Btn onClick={() => onCmd({ i_ref_max: parseFloat(imax) })}>Apply</Btn>
    </CtrlRow>
    <div className="smps-quickbar">
      <Btn onClick={() => onCmd({ enable: 1, vb_target: 9.5 })}>On (9.5V)</Btn>
      <Btn variant="danger" onClick={() => onCmd({ vb_target: 0 })}>Off</Btn>
      <Btn variant="warn" onClick={() => onCmd({ reset_trip: 1 })}>⚠ Reset Trip</Btn>
    </div>
  </>;
}

function ExportControls({ onCmd }) {
  const [vbt,  setVbt]  = useState('10.5');
  const [imax, setImax] = useState('2.0');
  return <>
    <CtrlRow label="vb_target">
      <input className="smps-num-input" type="number" value={vbt} step="0.05" min="0" max="12"
             onChange={e => setVbt(e.target.value)} />
      <span className="smps-unit-hint">V</span>
      <Btn onClick={() => onCmd({ vb_target: parseFloat(vbt) })}>Apply</Btn>
    </CtrlRow>
    <CtrlRow label="i_ref_max">
      <input className="smps-num-input" type="number" value={imax} step="0.1" min="0" max="2"
             onChange={e => setImax(e.target.value)} />
      <span className="smps-unit-hint">A</span>
      <Btn onClick={() => onCmd({ i_ref_max: parseFloat(imax) })}>Apply</Btn>
    </CtrlRow>
    <div className="smps-quickbar">
      <Btn onClick={() => onCmd({ enable: 1, vb_target: 10.5 })}>On (10.5V)</Btn>
      <Btn variant="danger" onClick={() => onCmd({ vb_target: 0 })}>Off</Btn>
      <Btn variant="warn" onClick={() => onCmd({ reset_trip: 1 })}>⚠ Reset Trip</Btn>
    </div>
  </>;
}

function CapControls({ onCmd }) {
  const [icmd, setIcmd] = useState(0);
  const sign = icmd >= 0 ? '+' : '';
  const apply = v => { setIcmd(v); onCmd({ i_cmd: v }); };
  return <>
    <CtrlRow label="i_cmd">
      <input className="smps-slider" type="range" min="-0.60" max="0.60" step="0.01"
             value={icmd} onChange={e => setIcmd(parseFloat(e.target.value))} />
      <span className="smps-now">{sign}{icmd.toFixed(2)} A</span>
      <Btn onClick={() => onCmd({ i_cmd: icmd })}>Apply</Btn>
    </CtrlRow>
    <div className="smps-quickbar">
      <Btn onClick={() => apply(0.20)}>Charge 0.2A</Btn>
      <Btn onClick={() => apply(-0.20)}>Discharge 0.2A</Btn>
      <Btn onClick={() => apply(0)}>Stop</Btn>
    </div>
    <div className="smps-quickbar">
      <Btn onClick={() => onCmd({ enable: 1 })}>Enable</Btn>
      <Btn variant="danger" onClick={() => onCmd({ enable: 0, i_cmd: 0 })}>Disable</Btn>
      <Btn variant="warn" onClick={() => onCmd({ reset_trip: 1 })}>⚠ Reset Trip</Btn>
    </div>
  </>;
}

function LEDControls({ onCmd }) {
  const [p, setP] = useState({ red: 0, yel: 0, grn: 0 });
  const upd = (ch, v) => setP(prev => ({ ...prev, [ch]: v }));
  return <>
    {['red', 'yel', 'grn'].map(c => (
      <CtrlRow key={c} label={`p_${c}`}>
        <input className="smps-slider" type="range" min="0" max="3" step="0.05"
               value={p[c]} onChange={e => upd(c, parseFloat(e.target.value))} />
        <span className="smps-now">{p[c].toFixed(2)} W</span>
        <Btn onClick={() => onCmd({ ['p_' + c]: p[c] })}>Apply</Btn>
      </CtrlRow>
    ))}
    <div className="smps-quickbar">
      <Btn onClick={() => {
        setP({ red: 0, yel: 0, grn: 0 });
        onCmd({ p_red: 0, p_yel: 0, p_grn: 0 });
      }}>All Off</Btn>
      <Btn onClick={() => onCmd({ enable: 1 })}>Enable</Btn>
      <Btn variant="warn" onClick={() => onCmd({ reset_trip: 1 })}>⚠ Reset Trip</Btn>
    </div>
  </>;
}

function LuxControls({ onCmd }) {
  return <>
    <CtrlRow label="Step 1">
      <Btn onClick={() => onCmd({ calibrate: 'dark' })}>Set 0% (lamp OFF)</Btn>
    </CtrlRow>
    <CtrlRow label="Step 2">
      <Btn onClick={() => onCmd({ calibrate: 'full' })}>Set 100% (lamp FULL)</Btn>
    </CtrlRow>
    <div className="smps-quickbar">
      <Btn variant="warn" onClick={() => {
        if (window.confirm('Wipe calibration data on the ESP32?'))
          onCmd({ calibrate: 'reset' });
      }}>⚠ Reset calibration</Btn>
    </div>
  </>;
}

// ─── Module card ─────────────────────────────────────────────────────────────

function ModuleCard({ role, data, history, onCmd }) {
  const color = ROLE_COLORS[role];
  const label = ROLE_LABELS[role];
  const lines = MOD_CHART_LINES[role] || [];

  const statsNode = {
    pv:     <PVStats     d={data} />,
    grid:   <GridStats   d={data} />,
    export: <ExportStats d={data} />,
    cap:    <CapStats    d={data} />,
    led:    <LEDStats    d={data} />,
    lux:    <LuxStats    d={data} />,
  }[role];

  const ctrlNode = {
    pv:     <PVControls     d={data} onCmd={onCmd} />,
    grid:   <GridControls           onCmd={onCmd} />,
    export: <ExportControls         onCmd={onCmd} />,
    cap:    <CapControls            onCmd={onCmd} />,
    led:    <LEDControls            onCmd={onCmd} />,
    lux:    <LuxControls            onCmd={onCmd} />,
  }[role];

  return (
    <div
      className={[
        'smps-card',
        !data          ? 'smps-card-offline' : '',
        data?.trip     ? 'smps-card-trip'    : '',
      ].join(' ')}
      style={{ borderTopColor: color }}
    >
      {/* Header */}
      <div className="smps-card-header">
        <span className="smps-card-title" style={{ color }}>{label}</span>
        <StatusPill d={data} role={role} />
      </div>

      {/* Trip banner */}
      {data?.trip && (
        <div className="smps-trip-banner">
          ⚠ TRIP · reason: <strong>{data.trip_reason || 'unknown'}</strong>
          &nbsp;· auto-recovers once fault clears
        </div>
      )}

      {/* Telemetry stats */}
      <div className="smps-stats-grid">
        {statsNode || (
          <div className="smps-offline-msg">No data — module offline</div>
        )}
      </div>

      {/* Mini chart */}
      {history.length > 1 && lines.length > 0 && (
        <div className="smps-chart-wrap">
          <ResponsiveContainer width="100%" height={110}>
            <LineChart data={history} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <XAxis hide />
              <YAxis tick={{ fontSize: 9, fill: '#555' }} width={36} />
              <Tooltip
                contentStyle={{
                  background: '#0d0d0d', border: '1px solid #2c2c2c',
                  borderRadius: 4, fontSize: 11,
                }}
                itemStyle={{ color: '#e6e6e6' }}
              />
              {lines.map(l => (
                <Line
                  key={l.key} type="linear" dataKey={l.key}
                  stroke={l.color} strokeWidth={1.5}
                  dot={false} name={l.label}
                  connectNulls={false} isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div className="smps-chart-legend">
            {lines.map(l => (
              <span key={l.key}>
                <span className="smps-swatch" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="smps-controls">
        {ctrlNode}
      </div>
    </div>
  );
}

// ─── Root component ───────────────────────────────────────────────────────────

export default function SmpsModules({ apiBase }) {
  const [hosts, setHosts] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('smps-module-hosts') || 'null') || { ...DEFAULT_HOSTS };
    } catch {
      return { ...DEFAULT_HOSTS };
    }
  });
  const [showHosts, setShowHosts] = useState(false);
  const [modules,   setModules]   = useState({});

  // Client-side rolling history (avoids extra backend poll per-role)
  const histRef  = useRef(Object.fromEntries(ROLES.map(r => [r, []])));
  const [hist, setHist] = useState(Object.fromEntries(ROLES.map(r => [r, []])));

  const saveHosts = () => {
    localStorage.setItem('smps-module-hosts', JSON.stringify(hosts));
    setShowHosts(false);
  };

  // Poll /modules/latest every 2 s; accumulate rolling history client-side
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`${apiBase}/modules/latest`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        setModules(data);
        ROLES.forEach(role => {
          if (data[role]) {
            const h = histRef.current[role];
            h.push(data[role]);
            if (h.length > HIST_MAX) h.shift();
          }
        });
        setHist(Object.fromEntries(ROLES.map(r => [r, [...histRef.current[r]]])));
      } catch { /* module offline or backend down */ }
    }
    poll();
    const id = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(id); };
  }, [apiBase]);

  // Send a command directly to a module's /cmd endpoint (CORS: * is set by firmware)
  const sendCmd = async (role, payload) => {
    let host = (hosts[role] || '').trim();
    if (!host) return;
    if (!host.startsWith('http')) host = 'http://' + host;
    try {
      await fetch(`${host}/cmd`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(2000),
      });
    } catch (e) {
      console.warn(`[smps] cmd to ${role} failed:`, e.message);
    }
  };

  return (
    <div className="smps-root">

      {/* Host configuration bar */}
      <div className="smps-host-bar">
        <button className="smps-host-toggle" onClick={() => setShowHosts(v => !v)}>
          {showHosts ? 'Hide host config' : 'Configure module hosts'}
        </button>
        {showHosts && (
          <div className="smps-host-panel">
            <p className="smps-host-hint">
              Hostname or IP for each module's HTTP server (used for sending commands).
              Backend collects telemetry via WiFi automatically.
            </p>
            <div className="smps-host-grid">
              {ROLES.map(r => (
                <div key={r} className="smps-host-row">
                  <label>{r}</label>
                  <input
                    value={hosts[r] || ''}
                    placeholder={DEFAULT_HOSTS[r]}
                    onChange={e => setHosts(h => ({ ...h, [r]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
            <button className="smps-host-save" onClick={saveHosts}>Save hosts</button>
          </div>
        )}
      </div>

      {/* Module cards */}
      <div className="smps-grid">
        {ROLES.map(role => (
          <ModuleCard
            key={role}
            role={role}
            data={modules[role] || null}
            history={hist[role]}
            onCmd={payload => sendCmd(role, payload)}
          />
        ))}
      </div>
    </div>
  );
}
