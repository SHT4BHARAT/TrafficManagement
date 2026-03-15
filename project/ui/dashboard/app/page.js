"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";

const JunctionVisualizer = ({ metrics, overrideLights }) => {
  const lanes = ['N', 'S', 'E', 'W'];

  if (!metrics) {
    return (
      <div className="junction-box loading">
        <div className="flex-center flex-col gap-2">
          <div className="pulse-icon large"></div>
          <span className="loading-text">SYNCHRONIZING TACTICAL DATA...</span>
        </div>
      </div>
    );
  }

  // Use overrideLights (effectiveLights from parent) when available for instant UI response
  const activeLights = overrideLights ?? (Array.isArray(metrics?.green_lights) ? metrics.green_lights : []);
  const cycleCountdown = metrics?.cycle_countdown ?? 0;
  const isNSActive = activeLights.includes("N") || activeLights.includes("S");
  const isEWActive = activeLights.includes("E") || activeLights.includes("W");

  // Sector status from congestion (same logic as sector cards): green = flowing/low, orange = congested, red = critical
  const queues = metrics?.queues || {};
  const maxPressure = Math.max(...lanes.map(l => (queues[l] || 0) / 30), 0);
  const anyGreen = activeLights.length > 0;
  let sectorStatus = 'green'; // flowing
  if (maxPressure > 0.8) sectorStatus = 'red';
  else if (maxPressure > 0.4 || !anyGreen) sectorStatus = 'orange';

  const sectorColors = {
    green: { fill: 'rgba(34, 197, 94, 0.12)', stroke: 'rgba(34, 197, 94, 0.7)' },
    orange: { fill: 'rgba(245, 158, 11, 0.12)', stroke: 'rgba(245, 158, 11, 0.7)' },
    red: { fill: 'rgba(244, 63, 94, 0.12)', stroke: 'rgba(244, 63, 94, 0.7)' }
  };
  const sector = sectorColors[sectorStatus];

  // Signal colour: green, orange (amber when countdown <= 3), red
  const getSignalColor = (lane) => {
    const isGreen = activeLights.includes(lane);
    if (!isGreen) return { fill: '#f43f5e', filter: 'drop-shadow(0 0 5px rgba(244, 63, 94, 0.5))' }; // red
    if (cycleCountdown <= 3 && cycleCountdown > 0) return { fill: '#f59e0b', filter: 'drop-shadow(0 0 8px rgba(245, 158, 11, 0.6))' }; // orange/amber
    return { fill: '#22c55e', filter: 'drop-shadow(0 0 10px rgba(34, 197, 94, 0.5))' }; // green
  };

  // Right-hand traffic: vehicles on the right side of the road in direction of travel
  // N lane: flow is southbound (down) → right side = west → lower x (90)
  // S lane: flow is northbound (up) → right side = east → higher x (110)
  // E lane: flow is westbound (left) → right side = north → lower y (90)
  // W lane: flow is eastbound (right) → right side = south → higher y (110)
  const vehicleX = { N: 90, S: 110, E: null, W: null };
  const vehicleY = { N: null, S: null, E: 90, W: 110 };

  return (
    <div className="junction-box" style={{ background: 'transparent' }}>
      <svg viewBox="0 0 200 200" className="junction-svg">
        {/* Sector circle - colour by status (green / orange / red) */}
        <circle cx="100" cy="100" r="102" fill={sector.fill} stroke={sector.stroke} strokeWidth="2" />

        <rect x="80" y="0" width="40" height="200"
          fill={isNSActive ? 'rgba(34, 197, 94, 0.15)' : '#0f172a'}
          stroke={isNSActive ? 'var(--secondary)' : 'transparent'} strokeWidth="1" />
        <rect x="0" y="80" width="200" height="40"
          fill={isEWActive ? 'rgba(34, 197, 94, 0.15)' : '#0f172a'}
          stroke={isEWActive ? 'var(--secondary)' : 'transparent'} strokeWidth="1" />

        <line x1="100" y1="0" x2="100" y2="75" stroke="#334155" strokeDasharray="4" />
        <line x1="100" y1="125" x2="100" y2="200" stroke="#334155" strokeDasharray="4" />
        <line x1="0" y1="100" x2="75" y2="100" stroke="#334155" strokeDasharray="4" />
        <line x1="125" y1="100" x2="200" y2="100" stroke="#334155" strokeDasharray="4" />

        {/* Signals: green, red, or orange (amber when countdown <= 3) */}
        {lanes.map(lane => {
          const isGreen = activeLights.includes(lane);
          const signalStyle = getSignalColor(lane);
          let pos = {};
          if (lane === 'N') pos = { x: 85, y: 75 };
          if (lane === 'S') pos = { x: 115, y: 125 };
          if (lane === 'E') pos = { x: 125, y: 85 };
          if (lane === 'W') pos = { x: 75, y: 115 };
          return (
            <circle key={lane} cx={pos.x} cy={pos.y} r="5"
              fill={signalStyle.fill}
              className={isGreen && cycleCountdown > 3 ? 'pulse-green' : ''}
              style={{ filter: signalStyle.filter }}
            />
          );
        })}

        {/* Vehicles: white, on right-hand side of each approach */}
        {lanes.map(lane => {
          const isGreen = activeLights.includes(lane);
          const density = metrics?.queues?.[lane] || 0;
          const dotsCount = Math.ceil(density / 2);
          const xOff = vehicleX[lane];
          const yOff = vehicleY[lane];

          return Array.from({ length: 20 }).map((_, i) => {
            const isVisible = i < dotsCount;
            let pos = { x: 0, y: 0 };
            let style = {};

            if (isGreen) {
              if (lane === 'N') pos = { x: xOff, y: -10 };
              if (lane === 'S') pos = { x: xOff, y: 210 };
              if (lane === 'E') pos = { x: 210, y: yOff };
              if (lane === 'W') pos = { x: -10, y: yOff };
              style = {
                animationName: `flow-${lane.toLowerCase()}`,
                animationDuration: `${Math.max(4, 8 - (density / 5))}s`,
                animationTimingFunction: 'linear',
                animationIterationCount: 'infinite',
                animationDelay: `${i * 1.5}s`
              };
            } else {
              const offset = i * 15;
              if (lane === 'N') pos = { x: xOff, y: Math.max(0, 65 - offset) };
              if (lane === 'S') pos = { x: xOff, y: Math.min(200, 135 + offset) };
              if (lane === 'E') pos = { x: Math.min(200, 135 + offset), y: yOff };
              if (lane === 'W') pos = { x: Math.max(0, 65 - offset), y: yOff };
            }

            return (
              <circle key={`${lane}-${i}`} cx={pos.x} cy={pos.y} r="3"
                fill="#ffffff"
                className={`traffic-dot dot-${lane.toLowerCase()}`}
                style={{
                  ...style,
                  opacity: isVisible ? (isGreen ? 0.9 : 1) : 0,
                  visibility: isVisible ? 'visible' : 'hidden',
                  filter: 'drop-shadow(0 0 6px rgba(255,255,255,0.9))'
                }}
              />
            );
          });
        })}
      </svg>
    </div>
  );
};

export default function DashboardV3() {
  const [mounted, setMounted] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [vps, setVps] = useState({ N: 14, S: 11, E: 6, W: 22 });
  const [ctrlMode, setCtrlMode] = useState("manual"); // "manual" | "auto"
  const [autoVps, setAutoVps] = useState({ N: 14, S: 11, E: 6, W: 22 });
  const autoVpsTimer = useRef(null);
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingSecs, setLoadingSecs] = useState(0);
  const loadingTimer = useRef(null);
  const [chatQuery, setChatQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [wsStatus, setWsStatus] = useState("connecting"); // FIX Bug 10
  const [slmStatus, setSlmStatus] = useState(null); // null = not checked, { ok, message } from /api/slm-status
  const [pendingPhase, setPendingPhase] = useState(null); // optimistic: "N"|"S"|"E"|"W"|"N-S"|"E-W" until metrics confirm
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  // FIX Bug 7: stable addLog via useCallback so socket closure always has fresh ref
  const addLog = useCallback((type, msg) => {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setLog(prev => [{ time, type, msg }, ...prev].slice(0, 20));
  }, []);

  // FIX Bug 10: WebSocket with auto-reconnect
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket("ws://localhost:8000/ws");
    wsRef.current = socket;

    socket.onopen = () => {
      setWsStatus("connected");
      addLog("auto", "COMM_CHANNEL established. Tactical stream active.");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics(data);
      if (data.events && data.events.length > 0) {
        data.events.forEach(e => addLog(e.type, e.msg));
      }
    };

    socket.onclose = () => {
      setWsStatus("reconnecting");
      addLog("error", "COMM_CHANNEL lost. Reconnecting in 3s...");
      reconnectTimer.current = setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, [addLog]);

  useEffect(() => {
    setMounted(true);
    addLog("ai-b", "Action B (Duration) node status: READY");
    connectWebSocket();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connectWebSocket, addLog]);

  // Sync controller mode and VPS with backend
  const pushControllerConfig = useCallback((mode, vpsPayload) => {
    fetch("http://localhost:8000/api/controller-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, vps: vpsPayload ?? undefined }),
    }).catch(() => {});
  }, []);

  // Auto mode: randomise VPS for each lane every 2s within [2, 40]
  useEffect(() => {
    if (ctrlMode === "auto") {
      pushControllerConfig("auto");
      const tick = () => {
        const next = {
          N: Math.floor(Math.random() * 39) + 2,
          S: Math.floor(Math.random() * 39) + 2,
          E: Math.floor(Math.random() * 39) + 2,
          W: Math.floor(Math.random() * 39) + 2,
        };
        setAutoVps(next);
      };
      tick();
      autoVpsTimer.current = setInterval(tick, 2000);
    } else {
      clearInterval(autoVpsTimer.current);
      pushControllerConfig("manual", vps);
    }
    return () => clearInterval(autoVpsTimer.current);
  }, [ctrlMode, pushControllerConfig]);

  // When in manual mode, push VPS to backend when user changes values (debounced)
  useEffect(() => {
    if (ctrlMode !== "manual") return;
    const t = setTimeout(() => pushControllerConfig("manual", vps), 800);
    return () => clearTimeout(t);
  }, [ctrlMode, vps, pushControllerConfig]);

  // Check SLM (Ollama) status for dashboard indicator
  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;
    fetch("http://localhost:8000/api/slm-status")
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setSlmStatus(data); })
      .catch(() => { if (!cancelled) setSlmStatus({ ok: false, message: "Backend unreachable" }); });
    return () => { cancelled = true; };
  }, [mounted]);

  // Clear pendingPhase when metrics confirm the selection — must be before early return
  useEffect(() => {
    if (!pendingPhase || !metrics?.green_lights) return;
    const gl = metrics.green_lights;
    const matches =
      (pendingPhase === "N-S" && gl.length === 2 && gl.includes("N") && gl.includes("S")) ||
      (pendingPhase === "E-W" && gl.length === 2 && gl.includes("E") && gl.includes("W")) ||
      (["N","S","E","W"].includes(pendingPhase) && gl.length === 1 && gl[0] === pendingPhase);
    if (matches) setPendingPhase(null);
  }, [metrics?.green_lights, pendingPhase]);

  if (!mounted) return null;

  // Raw lights from backend
  const activeLights = Array.isArray(metrics?.green_lights) ? metrics.green_lights : [];

  // effectiveLights: use pendingPhase optimistically so junction + sector cards update instantly on click
  const pendingToLights = (p) => {
    if (!p) return null;
    if (p === "N-S") return ["N", "S"];
    if (p === "E-W") return ["E", "W"];
    if (["N","S","E","W"].includes(p)) return [p];
    return null;
  };
  const effectiveLights = pendingToLights(pendingPhase) ?? activeLights;

  const singleGreen = effectiveLights.length === 1 ? effectiveLights[0] : null;
  const isNSPair = effectiveLights.length === 2 && effectiveLights.includes("N") && effectiveLights.includes("S");
  const isEWPair = effectiveLights.length === 2 && effectiveLights.includes("E") && effectiveLights.includes("W");
  const laneNames = { N: "NORTH", S: "SOUTH", E: "EAST", W: "WEST" };
  const heldLanes = ["N", "S", "E", "W"].filter((l) => !effectiveLights.includes(l));
  const activeAxisDisplay = isNSPair ? "NORTH-SOUTH" : isEWPair ? "EAST-WEST" : singleGreen ? `${laneNames[singleGreen]} (${singleGreen})` : "ROTATING...";
  const heldLanesDisplay = heldLanes.length ? `${heldLanes.join("+")} HELD` : "—";

  // Button active states
  const showActive = (lane) => effectiveLights.length === 1 && effectiveLights[0] === lane;
  const showNSPairActive = isNSPair;
  const showEWPairActive = isEWPair;

  const handlePhaseSelect = async (phase) => {
    setPendingPhase(phase);
    addLog("act-a", `SELECT_PHASE: ${phase}`);
    try {
      await fetch("http://localhost:8000/api/select-phase", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase })
      });
      addLog("auto", `Actuation verified: ${phase} active.`);
    } catch {
      addLog("error", "Error: Phase switch command timed out.");
      setPendingPhase(null);
    }
  };

  const handleAskAI = async () => {
    setLoading(true);
    setLoadingSecs(0);
    loadingTimer.current = setInterval(() => setLoadingSecs(s => s + 1), 1000);
    addLog("auto", "Querying TrafficAgent SLM (CPU inference ~60-120s)...");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 200000); // 200s — CPU inference is slow
    try {
      const activePhase = effectiveLights.join("-") || "N-S";
      const activeVps = ctrlMode === "auto" ? autoVps : vps;
      const response = await fetch("http://localhost:8000/api/ai-inference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: activePhase, vps: activeVps }),
        signal: controller.signal
      });
      const data = await response.json();
      if (data.status === "error") {
        addLog("error", `INF_ERROR: ${data.message || data.reasoning || "Model unavailable."}`);
      } else {
        addLog("ai-b", `INF_RESULT: ${data.duration}s queued for next cycle.`);
        addLog("ai-b", `REASON: ${data.reasoning}`);
        if (data.status === "fallback") {
          addLog("auto", "NOTE: Ollama offline — local heuristic used.");
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        addLog("error", "ERROR: Inference timed out. Model may still be loading.");
      } else {
        addLog("error", "ERROR: Inference engine offline or malformed response.");
      }
    } finally {
      clearTimeout(timeout);
      clearInterval(loadingTimer.current);
      setLoading(false);
      setLoadingSecs(0);
    }
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;
    const userMsg = chatQuery;
    setChatQuery("");
    setChatLoading(true);
    addLog("user", `> ${userMsg}`);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 200000);
    try {
      const response = await fetch("http://localhost:8000/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg }),
        signal: controller.signal
      });
      const data = await response.json();
      if (data.answer) addLog("ai", data.answer);
      if (data.recommendation) addLog("ai", `Recommendation: ${data.recommendation}`);
      if (data.status === "EMERGENCY_ACTIVE") {
        addLog("error", "[SYSTEM] EMERGENCY OVERRIDE ENGAGED");
      }
    } catch (err) {
      if (err.name === "AbortError") {
        addLog("error", "SLM TIMEOUT: No response in 15s. Is Ollama running?");
      } else {
        addLog("error", "SYSTEM OFFLINE: Local Agent Unreachable");
      }
    } finally {
      clearTimeout(timeout);
      setChatLoading(false);
    }
  };

  // Manual mode: each lane is independently editable
  const handleVpsChange = (lane, value) => {
    setVps(prev => ({ ...prev, [lane]: parseInt(value) || 0 }));
  };

  return (
    <div className="dashboard-shell">
      <aside className="command-sidebar" aria-label="Navigation">
        <div className="side-icon glow-primary" title="Tactical feed">🛰️</div>
        <div className="side-icon" title="Junctions">🚦</div>
        <div className="side-icon" title="Map">🗺️</div>
        <div className="side-icon" title="Settings">⚙️</div>
        <div style={{ marginTop: 'auto' }} className="side-icon" title="Profile">👤</div>
      </aside>

      <main className="main-theater">
        <header className="hud-header" style={{ flexShrink: 0 }}>
          <div className="flex-col">
            <h1 className="hud-title" style={{ fontSize: '1.2rem' }}>DAITFO</h1>
            <p className="text-cyan" style={{ fontSize: '0.6rem', letterSpacing: '2.5px', fontWeight: 'bold' }}>
              TRANSIT OPTIMIZATION ENGINE v3.5 · SCOOT ALGORITHMIC CONTROL
            </p>
          </div>
          <div className="header-badges">
            <span className="badge-v3 active">SCOOT_TUNING</span>
            <span className="badge-v3 mtls">MTLS: VALID</span>
            <span className="badge-v3 ai">AI: SUPERVISOR</span>
            {slmStatus != null && (
              slmStatus.ok && slmStatus.model_available !== false ? (
                <span className="badge-v3" style={{ borderColor: 'var(--secondary)', color: 'var(--secondary)', background: 'rgba(34,197,94,0.1)' }} title={slmStatus.message}>SLM: READY</span>
              ) : (
                <span className="badge-v3" style={{ borderColor: 'var(--warning)', color: 'var(--warning)', background: 'rgba(245,158,11,0.1)' }} title={slmStatus.message || slmStatus.error}>SLM: OFFLINE</span>
              )
            )}
            {wsStatus === "connecting" && (
              <span className="badge-v3" style={{ borderColor: 'var(--warning)', color: 'var(--warning)', background: 'rgba(245,158,11,0.1)' }}>CONNECTING...</span>
            )}
            {wsStatus === "reconnecting" && (
              <span className="badge-v3 emergency pulse-red">WS: RECONNECTING</span>
            )}
            {metrics?.emergency?.active && (
              <span className="badge-v3 emergency pulse-red">EMERGENCY_ACTIVE</span>
            )}
            <div className="phase-clock-v3" title="Cycle countdown">
              PHASE: {metrics?.cycle_countdown ?? 0}s
            </div>
          </div>
        </header>

        <div className="main-theater-scroll">
        <section className="telemetry-grid">
            <div className="stat-vessel">
            <span className="stat-label">SYS UPTIME</span>
            <div className="stat-value" style={{ color: 'var(--secondary)' }}>{metrics?.uptime ?? "99.99%"}</div>
            <div style={{ fontSize: '0.55rem', opacity: 0.5 }}>STABLE</div>
          </div>
          <div className="stat-vessel">
            <span className="stat-label">COORD. PI</span>
            <div className="stat-value text-cyan">{metrics?.pi ?? "4.20"}</div>
            <div style={{ fontSize: '0.55rem', opacity: 0.5 }}>PERF_INDEX_SCORE</div>
          </div>
          <div className="stat-vessel">
            <span className="stat-label">AI DURATION</span>
            <div className="stat-value" style={{ color: '#a855f7' }}>{metrics?.ai_duration ?? 35}s</div>
            <div style={{ fontSize: '0.55rem', opacity: 0.5 }}>QUEUED_NEXT_CYCLE</div>
          </div>
          <div className="stat-vessel">
            <span className="stat-label">AVG WAIT</span>
            <div className="stat-value" style={{ color: (metrics?.avg_wait && parseFloat(String(metrics.avg_wait).replace('s','')) > 60) ? 'var(--accent)' : 'var(--warning)' }}>
              {metrics?.avg_wait ?? "0.0s"}
            </div>
            <div style={{ fontSize: '0.55rem', opacity: 0.5 }}>RED LANES ONLY</div>
          </div>
        </section>

        <div className="main-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '16px' }}>
          <section className="glass-card tactical-map">
            <div style={{ position: 'absolute', top: '15px', left: '20px', right: '20px', zIndex: 1 }}>
              <p className="stat-label" style={{ fontSize: '0.6rem' }}>{metrics?.intersection ?? "INT_001 · MAIN ST & BROADWAY"} · LATENCY: 4ms</p>
            </div>
            <div className="map-container" style={{ width: '280px', height: '280px' }}>
              <div className="map-scan-line"></div>
              <JunctionVisualizer metrics={metrics} overrideLights={effectiveLights} />
            </div>
            <div style={{ display: 'flex', gap: '20px', marginTop: '20px', fontSize: '0.6rem', flexWrap: 'wrap' }}>
              <span className="flex items-center gap-2"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--secondary)' }}></div> GREEN</span>
              <span className="flex items-center gap-2"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--warning)' }}></div> ORANGE</span>
              <span className="flex items-center gap-2"><div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)' }}></div> RED</span>
              <span className="flex items-center gap-2"><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff', boxShadow: '0 0 6px rgba(255,255,255,0.9)' }}></div> VEHICLE</span>
            </div>
          </section>

          <section className="glass-card controller-card" style={{ padding: '24px' }}>
            <h3 className="hud-title" style={{ fontSize: '0.8rem', marginBottom: '16px' }}>TRAFFIC CONTROLLER</h3>

            {/* Mode toggle */}
            <div className="ctrl-mode-toggle">
              <button
                className={`ctrl-mode-btn ${ctrlMode === "manual" ? "active-manual" : ""}`}
                onClick={() => { setCtrlMode("manual"); addLog("auto", "Controller switched to MANUAL mode."); }}
              >MANUAL</button>
              <button
                className={`ctrl-mode-btn ${ctrlMode === "auto" ? "active-auto" : ""}`}
                onClick={() => { setCtrlMode("auto"); addLog("auto", "Controller switched to AUTO mode. VPS randomising 2–40."); }}
              >AUTO</button>
            </div>

            {ctrlMode === "manual" ? (
              <>
                <div className="action-step">
                  <span className="action-header">ACTION A · PHASE SELECT</span>
                  <p style={{ fontSize: '0.6rem', opacity: 0.6, marginBottom: '10px' }}>Single direction or axis pair. Choose:</p>
                  <div className="phase-grid-four">
                    {["N", "S", "E", "W"].map((lane) => (
                      <button
                        key={lane}
                        onClick={() => handlePhaseSelect(lane)}
                        className={`phase-btn ${showActive(lane) ? "active" : ""}`}
                      >{lane}</button>
                    ))}
                  </div>
                  <div className="phase-toggle-group" style={{ marginTop: '8px' }}>
                    <button
                      onClick={() => handlePhaseSelect("N-S")}
                      className={`phase-btn ${showNSPairActive ? "active" : ""}`}
                    >N-S</button>
                    <button
                      onClick={() => handlePhaseSelect("E-W")}
                      className={`phase-btn ${showEWPairActive ? "active" : ""}`}
                    >E-W</button>
                  </div>
                  <p style={{ fontSize: '0.6rem', opacity: 0.5, marginTop: '8px' }}>
                    {(() => {
                      const single = ["N","S","E","W"].find(l => showActive(l));
                      if (single) return `${laneNames[single]} green. ${["N","S","E","W"].filter(l => l !== single).join("+")} HELD.`;
                      if (showNSPairActive) return "N+S green. E+W HELD.";
                      if (showEWPairActive) return "E+W green. N+S HELD.";
                      return `Mode: ${activeAxisDisplay}`;
                    })()}
                  </p>
                </div>

                <div className="action-step" style={{ marginTop: '20px' }}>
                  <span className="action-header">
                    <span style={{ transform: 'rotate(90deg)', display: 'inline-block' }}>↺</span> ACTION B · AI DURATION
                  </span>
                  <p style={{ fontSize: '0.65rem', opacity: 0.5, marginBottom: '12px' }}>Live VPS inputs (editable):</p>
                  <div className="vps-input-row">
                    <div className="vps-field"><label>N VPS</label><input type="number" min="0" max="99" value={vps.N} onChange={e => handleVpsChange('N', e.target.value)} /></div>
                    <div className="vps-field"><label>S VPS</label><input type="number" min="0" max="99" value={vps.S} onChange={e => handleVpsChange('S', e.target.value)} /></div>
                  </div>
                  <div className="vps-input-row" style={{ marginTop: '8px' }}>
                    <div className="vps-field"><label>E VPS</label><input type="number" min="0" max="99" value={vps.E} onChange={e => handleVpsChange('E', e.target.value)} /></div>
                    <div className="vps-field"><label>W VPS</label><input type="number" min="0" max="99" value={vps.W} onChange={e => handleVpsChange('W', e.target.value)} /></div>
                  </div>
                  <div style={{ margin: '20px 0', borderBottom: '1px solid var(--glass-border)' }}></div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--warning)' }}>{metrics?.ai_duration ?? 35}s</span>
                    <span className="stat-label">queued for next cycle</span>
                  </div>
                  <p style={{ fontSize: '0.7rem', opacity: 0.6, margin: '12px 0', lineHeight: '1.4' }}>
                    {loading ? "Inference in progress..." : metrics?.ai_reasoning || "Press 'Ask AI' to queue a duration recommendation."}
                  </p>
                  <button onClick={handleAskAI} disabled={loading} className="glass-card"
                    style={{ width: '100%', padding: '14px', color: '#fff', fontFamily: 'var(--font-hud)', fontWeight: 'bold', fontSize: '0.8rem', letterSpacing: '2px', background: 'rgba(255,255,255,0.02)', cursor: 'pointer', border: '1px solid rgba(255,255,255,0.1)' }}>
                    {loading ? `INFERRING... ${loadingSecs}s` : "ASK AI FOR DURATION ↗"}
                  </button>
                </div>
              </>
            ) : (
              /* AUTO MODE */
              <>
                <div className="auto-badge">
                  <span className="auto-dot"></span>
                  AUTO · ROUND-ROBIN · 15s PER LANE
                </div>
                <p style={{ fontSize: '0.65rem', opacity: 0.5, marginBottom: '12px' }}>
                  Each lane gets <span style={{ color: '#a855f7' }}>15s</span> green in sequence (N → S → E → W). VPS randomly sampled <span style={{ color: '#a855f7' }}>2–40 vpm</span>.
                </p>

                {/* Active lane indicator */}
                <div style={{ marginBottom: '12px' }}>
                  <span className="stat-label" style={{ fontSize: '0.55rem' }}>ACTIVE LANE</span>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    {['N','S','E','W'].map(lane => {
                      const isActive = effectiveLights.length === 1 && effectiveLights[0] === lane;
                      return (
                        <div key={lane} style={{
                          flex: 1, textAlign: 'center', padding: '8px 4px',
                          borderRadius: '6px', fontWeight: 'bold', fontSize: '0.8rem',
                          fontFamily: 'var(--font-hud)',
                          background: isActive ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.03)',
                          border: `1px solid ${isActive ? 'var(--secondary)' : 'rgba(255,255,255,0.08)'}`,
                          color: isActive ? 'var(--secondary)' : 'rgba(255,255,255,0.3)',
                          transition: 'all 0.3s'
                        }}>{lane}</div>
                      );
                    })}
                  </div>
                  <div style={{ marginTop: '6px', fontSize: '0.6rem', opacity: 0.5 }}>
                    REMAINING: <span style={{ color: '#a855f7' }}>{metrics?.cycle_countdown ?? 15}s</span>
                  </div>
                </div>

                <div className="auto-vpm-row">
                  {['N','S','E','W'].map(lane => (
                    <div key={lane} className="auto-vpm-lane">
                      <span className="lane-label">LANE {lane}</span>
                      <span className="lane-val">{autoVps[lane]}</span>
                    </div>
                  ))}
                </div>
                <div style={{ margin: '16px 0', borderBottom: '1px solid var(--glass-border)' }}></div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                  <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#a855f7' }}>{metrics?.ai_duration ?? 35}s</span>
                  <span className="stat-label">AI duration (queued)</span>
                </div>
                <p style={{ fontSize: '0.7rem', opacity: 0.6, margin: '12px 0', lineHeight: '1.4' }}>
                  {metrics?.ai_reasoning || "AUTO mode active. Trigger AI to override next cycle duration."}
                </p>
                <button onClick={handleAskAI} disabled={loading} className="glass-card"
                  style={{ width: '100%', padding: '14px', color: '#a855f7', fontFamily: 'var(--font-hud)', fontWeight: 'bold', fontSize: '0.8rem', letterSpacing: '2px', background: 'rgba(168,85,247,0.04)', cursor: 'pointer', border: '1px solid rgba(168,85,247,0.3)', marginBottom: '8px' }}>
                  {loading ? `INFERRING... ${loadingSecs}s` : "TRIGGER AI INFERENCE ↗"}
                </button>
              </>
            )}
          </section>
        </div>

        <section className="zone-grid" style={{ marginTop: '12px' }}>
          {['N', 'S', 'E', 'W'].map((lane) => {
            const queueDepth = metrics?.queues?.[lane] || 0;
            // In manual mode, show the user-set VPS; in auto mode show backend's live VPM
            const incomingVPM = ctrlMode === "manual" ? vps[lane] : (metrics?.vpm?.[lane] || 0);
            const waitTime = metrics?.red_times?.[lane] || 0;
            const isGreen = effectiveLights.includes(lane);
            const predictedClearSecs = isGreen ? Math.ceil(queueDepth / 1.5) : 0;
            const pressureScore = queueDepth / 30;

            let statusClass = "";
            let statusLabel = "HOLDING";
            let barColor = "rgba(255,255,255,0.2)";

            if (isGreen) {
              statusClass = "active"; statusLabel = "FLOWING"; barColor = "var(--secondary)";
            } else if (pressureScore > 0.8) {
              statusClass = "heavy overflow"; statusLabel = "CRITICAL"; barColor = "var(--accent)";
            } else if (pressureScore > 0.4) {
              statusClass = "warning"; statusLabel = "CONGESTED"; barColor = "var(--warning)";
            }

            return (
              <div key={lane} className={`glass-card zone-card ${statusClass}`} style={{ padding: '12px 20px', transition: 'all 0.5s' }}>
                <div className="flex justify-between items-center" style={{ marginBottom: '8px' }}>
                  <div className="flex-col">
                    <span className="stat-label" style={{ fontSize: '0.6rem' }}>
                      SECTOR_{lane === 'N' ? 'N23' : lane === 'S' ? 'S22' : lane === 'E' ? 'E13' : 'W17'}
                    </span>
                    <div style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>
                      {lane === 'N' ? 'NORTH' : lane === 'S' ? 'SOUTH' : lane === 'E' ? 'EAST' : 'WEST'}
                    </div>
                  </div>
                  <span className={`badge-v3 ${isGreen ? 'active' : pressureScore > 0.8 ? 'heavy' : pressureScore > 0.4 ? 'warning' : ''}`}>
                    {statusLabel}
                  </span>
                </div>

                <div className="queue-telemetry" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                  <div className="mini-stat">
                    <span className="stat-label" style={{ fontSize: '0.5rem' }}>INCOMING (VPM)</span>
                    <div style={{ color: 'var(--primary)', fontWeight: 'bold' }}>
                      {metrics?.vpm == null ? '—' : `${incomingVPM}${incomingVPM > 0 ? '↑' : ''}`}
                    </div>
                  </div>
                  <div className="mini-stat">
                    <span className="stat-label" style={{ fontSize: '0.5rem' }}>BACKLOG (DEPTH)</span>
                    <div style={{ color: '#fff', fontWeight: 'bold' }}>{queueDepth}</div>
                  </div>
                </div>

                <div className="progress-bar-wrap" style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', marginBottom: '10px', position: 'relative', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${Math.min(pressureScore * 100, 100)}%`,
                    background: barColor, boxShadow: `0 0 10px ${barColor}`,
                    transition: 'width 0.8s ease-out, background 0.3s',
                    borderRadius: '3px'
                  }}></div>
                  <div aria-hidden="true" className="progress-threshold" style={{
                    position: 'absolute', left: '80%', top: 0, width: '2px', height: '100%',
                    background: 'rgba(244, 63, 94, 0.35)', borderRadius: 1
                  }} title="Critical threshold" />
                </div>

                <div className="sector-wait-row">
                  <span className="stat-label">
                    WAIT: <span style={{ color: waitTime > 60 ? 'var(--accent)' : '#94a3b8' }}>{waitTime > 0 ? `${waitTime}s` : '—'}</span>
                  </span>
                  <span className="stat-label sector-wait-right">
                    {isGreen
                      ? (predictedClearSecs > 0 ? `EST. CLEAR: ${predictedClearSecs}s` : '—')
                      : (metrics?.cycle_countdown > 0 ? `REMAINING: ${metrics.cycle_countdown}s` : '—')
                    }
                  </span>
                </div>
              </div>
            );
          })}
        </section>
        </div>
      </main>

      <footer className="bottom-terminal">
        <h3 className="stat-label" style={{ marginBottom: '12px', color: 'rgba(255,255,255,0.5)' }}>DECISION LOG</h3>
        <div className="log-terminal">
          {log.length === 0 ? (
            <div className="log-entry" style={{ color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>No entries yet. Waiting for stream...</div>
          ) : (
            log.map((entry, idx) => (
              <div key={idx} className={`log-entry ${entry.type}`} role="log">
                <span className="timestamp">[{entry.time}]</span>
                <span className="log-type">{entry.type.toUpperCase()}</span>
                {entry.msg}
              </div>
            ))
          )}
        </div>
        <form onSubmit={handleChatSubmit} style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
          <span style={{ color: 'var(--primary)', fontWeight: 'bold', alignSelf: 'center' }}>HQ_LINK {'>'}</span>
          <input
            type="text"
            value={chatQuery}
            onChange={(e) => setChatQuery(e.target.value)}
            placeholder="Enter manual command or query SLM..."
            className="chat-input-v3"
            disabled={chatLoading}
          />
          <button type="submit" className="chat-submit-v3" disabled={chatLoading}>
            {chatLoading ? '...' : 'SEND TO SLM ↗'}
          </button>
        </form>
      </footer>

      <style jsx>{`
        .action-step { position: relative; }
        .phase-toggle-group { display: flex; gap: 10px; }
        .phase-grid-four { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .phase-btn { flex: 1; min-width: 0; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 12px; border-radius: 6px; cursor: pointer; font-family: var(--font-hud); font-weight: bold; transition: all 0.3s; }
        .phase-btn.active { background: rgba(34, 197, 94, 0.1); border-color: var(--secondary); color: var(--secondary); box-shadow: inset 0 0 15px rgba(34, 197, 94, 0.1); }
        .chat-input-v3 { flex: 1; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 10px 15px; border-radius: 6px; font-family: monospace; outline: none; transition: border-color 0.3s; }
        .chat-input-v3:focus { border-color: var(--primary); }
        .chat-input-v3::placeholder { color: rgba(255,255,255,0.3); }
        .chat-submit-v3 { background: rgba(14, 165, 233, 0.1); border: 1px solid var(--primary); color: var(--primary); padding: 0 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-family: inherit; transition: all 0.3s; }
        .chat-submit-v3:hover:not(:disabled) { background: var(--primary); color: #000; box-shadow: 0 0 15px var(--primary); }
        .chat-submit-v3:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
        .phase-btn:focus-visible { outline: 2px solid var(--secondary); outline-offset: 2px; }
        .log-entry.user { color: #fff; opacity: 0.9; }
        .log-entry.ai { color: var(--primary); }
        .log-type { font-weight: 600; margin-right: 10px; font-size: 0.65rem; letter-spacing: 0.5px; opacity: 0.9; }
      `}</style>
    </div>
  );
}
