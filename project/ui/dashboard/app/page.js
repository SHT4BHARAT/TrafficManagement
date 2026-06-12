"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";

// Mock Data for fallback & interactive feel
const API_BASE = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
  : 'http://localhost:8000';
const WS_URL = API_BASE.replace(/^http/, 'ws');
const API_KEY = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_DAITFO_API_KEY || '')
  : '';
const MOCK_METRICS = {
  green_lights: ['N', 'S'],
  queues: { N: 12, S: 8, E: 25, W: 14 },
  vpm:    { N: 12, S: 8,  E: 25, W: 14 },
  cycle_countdown: 18
};

const VehicleFlow = ({ lane, count, isGreen, vpm = 10 }) => {
  // Render number of cars proportional to VPM (min 1, max 12 for visual performance)
  const visualCount = Math.max(1, Math.min(12, Math.ceil(vpm / 4)));
  const cars = Array.from({ length: visualCount }).map((_, i) => i);
  // duration = 60/VPM seconds per road traversal; clamped 0.5s–12s
  const animDuration = Math.max(0.5, Math.min(12, 60 / Math.max(1, vpm)));
  const getPath = (lane) => {
    // Indian LHD: vehicles keep LEFT. 
    // Road centerline at x=100 (N/S) and y=100 (E/W).
    // N-approaching (from bottom going up): left lane → x=90 (left of center)
    // S-approaching (from top going down): left lane → x=110 (right of center when facing up)
    // E-approaching (from left going right): left lane → y=90 (top of center, since they face right)
    // W-approaching (from right going left): left lane → y=110 (bottom of center, since they face left)
    switch(lane) {
      case 'N': return { x1: 90, y1: 200, x2: 90, y2: 0 };   // goes UP on left side
      case 'S': return { x1: 110, y1: 0, x2: 110, y2: 200 }; // goes DOWN on left side
      case 'E': return { x1: 0, y1: 90, x2: 200, y2: 90 };   // goes RIGHT on top half
      case 'W': return { x1: 200, y1: 110, x2: 0, y2: 110 }; // goes LEFT on bottom half
      default: return null;
    }
  };
  const p = getPath(lane);
  if (!p) return null;
  return (
    <g>
      {cars.map(i => (
        <rect key={i} width="8" height="14" rx="2" fill="var(--secondary)"
          style={{
            opacity: 0.9, filter: 'drop-shadow(0 0 8px var(--secondary))',
            offsetPath: `path('M ${p.x1} ${p.y1} L ${p.x2} ${p.y2}')`,
            animationName: isGreen ? 'vehicle-move' : 'none',
            animationDuration: `${animDuration.toFixed(2)}s`,
            animationTimingFunction: 'linear',
            animationIterationCount: 'infinite',
            animationDelay: `${i * 0.3}s`,
            offsetDistance: isGreen ? '0%' : '35%',
            visibility: !isGreen && i > 0 ? 'hidden' : 'visible'
          }}
        />
      ))}
    </g>
  );
};

const JunctionVisualizer = ({ metrics, size = "100%" }) => {
  const data = metrics || MOCK_METRICS;
  const activeLights = Array.isArray(data?.green_lights) ? data.green_lights : [];
  const queues = data?.queues || {};
  
  return (
    <div className="flex-1 flex justify-center items-center w-full h-full overflow-hidden relative" style={{ padding: '8px' }}>
      <style>{`@keyframes vehicle-move { from { offset-distance: 0%; } to { offset-distance: 100%; } }`}</style>
      
      {/* Tactical Compass (Top-Right High Contrast) */}
      <div className="absolute top-10 right-10 flex flex-col items-center opacity-90" style={{ border: '3px solid var(--primary)', borderRadius: '50%', width: '56px', height: '56px', justifyContent: 'center', background: 'var(--bg-card)', boxShadow: '0 0 25px var(--primary-glow)', zIndex: 100 }}>
         <span style={{ fontSize: '0.9rem', fontWeight: 900, color: 'var(--primary)', letterSpacing: '1px' }}>N</span>
         <div style={{ width: '4px', height: '16px', background: 'var(--primary)', marginTop: '-3px', borderRadius: '2px', boxShadow: '0 0 10px var(--primary)' }}></div>
      </div>

      <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%', maxWidth: 'calc(100vh - 356px)', maxHeight: 'calc(100vh - 356px)', aspectRatio: '1/1' }}>
        <defs>
          <radialGradient id="roadGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.15" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="100" cy="100" r="100" fill="url(#roadGlow)" />
        <circle cx="100" cy="100" r="95" fill="none" stroke="var(--primary)" strokeWidth="0.5" strokeDasharray="4,4" opacity="0.3" />
        
        {/* Roads */}
        <rect x="80" y="0" width="40" height="200" fill="rgba(148, 163, 184, 0.12)" rx="2" />
        <rect x="0" y="80" width="40" height="200" fill="rgba(148, 163, 184, 0.12)" rx="2" transform="rotate(-90 100 100)" />
        
        {/* Lane Markings */}
        <line x1="100" y1="0" x2="100" y2="80" stroke="var(--text-dim)" strokeDasharray="5" opacity="0.4" />
        <line x1="100" y1="120" x2="100" y2="200" stroke="var(--text-dim)" strokeDasharray="5" opacity="0.4" />
        <line x1="0" y1="100" x2="80" y2="100" stroke="var(--text-dim)" strokeDasharray="5" opacity="0.4" />
        <line x1="120" y1="100" x2="200" y2="100" stroke="var(--text-dim)" strokeDasharray="5" opacity="0.4" />
        
        {/* Orientation Labels (High Visibility & Inward for No-Clipping) */}
        <text x="100" y="30" textAnchor="middle" fill="var(--primary)" fontSize="14" fontWeight="900" style={{ filter: 'drop-shadow(0 0 5px var(--primary))', pointerEvents: 'none' }}>N</text>
        <text x="100" y="174" textAnchor="middle" fill="var(--primary)" fontSize="14" fontWeight="900" style={{ filter: 'drop-shadow(0 0 5px var(--primary))', pointerEvents: 'none' }}>S</text>
        <text x="170" y="105" textAnchor="middle" fill="var(--primary)" fontSize="14" fontWeight="900" style={{ filter: 'drop-shadow(0 0 5px var(--primary))', pointerEvents: 'none' }}>E</text>
        <text x="30" y="105" textAnchor="middle" fill="var(--primary)" fontSize="14" fontWeight="900" style={{ filter: 'drop-shadow(0 0 5px var(--primary))', pointerEvents: 'none' }}>W</text>

        {['N', 'S', 'E', 'W'].map(lane => (
          <VehicleFlow key={lane} lane={lane} count={queues[lane] || 0} isGreen={activeLights.includes(lane)} vpm={data?.vpm?.[lane] || 10} />
        ))}
        
        {['N', 'S', 'E', 'W'].map(lane => {
          const isG = activeLights.includes(lane);
          let pos = lane === 'N' ? { x: 88, y: 72 } : lane === 'S' ? { x: 112, y: 128 } : lane === 'E' ? { x: 128, y: 88 } : { x: 72, y: 112 };
          return (
            <g key={lane}>
              <circle cx={pos.x} cy={pos.y} r="7" fill={isG ? '#22c55e' : '#f43f5e'} style={{ filter: `drop-shadow(0 0 12px ${isG ? '#22c55e' : '#f43f5e'})` }} />
              {isG && (
                <circle cx={pos.x} cy={pos.y} r="9" fill="none" stroke="#22c55e" strokeWidth="1.5">
                  <animate attributeName="r" from="7" to="24" dur="1.2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.7" to="0" dur="1.2s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

const CityMap = ({ metrics, selectedNode, setSelectedNode }) => {
  const nodes = [];
  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 5; c++) {
      const id = `INT_${String(r * 5 + c + 1).padStart(3, '0')}`;
      nodes.push({ id, x: 150 + c * 175, y: 150 + r * 150, active: id === selectedNode });
    }
  }
  return (
    <div className="map-canvas-area flex-1 flex flex-col justify-center items-center relative">
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2 term-label" style={{ background: 'var(--primary-glow)', padding: '4px 20px', borderRadius: '20px', border: '1px solid var(--primary)' }}>
         ▲ NORTH TACTICAL GRID
      </div>
      <svg viewBox="0 0 1000 750" style={{ width: '95%', height: '95%' }}>
        {nodes.map((n, i) => {
          const nextRow = nodes.find(nn => nn.x === n.x && nn.y === n.y + 150);
          const nextCol = nodes.find(nn => nn.y === n.y && nn.x === n.x + 175);
          return (
            <React.Fragment key={i}>
              {nextRow && <line x1={n.x} y1={n.y} x2={nextRow.x} y2={nextRow.y} stroke="var(--primary)" strokeWidth="3" opacity="0.2" />}
              {nextCol && <line x1={n.x} y1={n.y} x2={nextCol.x} y2={nextCol.y} stroke="var(--primary)" strokeWidth="3" opacity="0.2" />}
            </React.Fragment>
          );
        })}
        {nodes.map(n => (
          <g key={n.id} transform={`translate(${n.x}, ${n.y})`} style={{ cursor: 'pointer' }} onClick={() => setSelectedNode(n.id)}>
            <circle r={n.active ? "36" : "18"} fill={n.active ? "var(--primary)" : "var(--bg-card)"} stroke="var(--primary)" strokeWidth="3" style={{ transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)' }} />
            {n.active && (
              <circle r="40" fill="none" stroke="var(--primary)" strokeWidth="1">
                <animate attributeName="r" from="36" to="60" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
              </circle>
            )}
            <text y="5" textAnchor="middle" fill={n.active ? "#fff" : "var(--text-main)"} fontSize="12" fontWeight="900" style={{ pointerEvents: 'none' }}>{n.id}</text>
            <text y="55" textAnchor="middle" fill="var(--text-dim)" fontSize="11" fontWeight="700" style={{ pointerEvents: 'none' }}>{n.active ? "SELECTED" : "STABLE"}</text>
          </g>
        ))}
      </svg>
    </div>
  );
};

export default function Dashboard() {
  const junctions = Array.from({ length: 20 }, (_, i) => `INT_${String(i + 1).padStart(3, '0')}`);
  const [activeTab, setActiveTab] = useState("junction");
  const [theme, setTheme] = useState("dark-theme");
  const [selectedNode, setSelectedNode] = useState("INT_001");
  const [metrics, setMetrics] = useState(null);
  const [log, setLog] = useState([]);
  const [ctrlMode, setCtrlMode] = useState("manual");
  const [vps, setVps] = useState({ N: 14, S: 11, E: 6, W: 22 });
  const [phaseDuration, setPhaseDuration] = useState(30);
  const [activePhase, setActivePhase] = useState('NS');
  const [slmAdvisory, setSlmAdvisory] = useState({ reasoning: "Awaiting analysis...", recommendation: "" });
  const [slmThinking, setSlmThinking] = useState(false);

  // Phase → green lights mapping; updates visualizer immediately without waiting for WebSocket
  const PHASE_MAP = { NS: ['N','S'], EW: ['E','W'], N:['N'], S:['S'], E:['E'], W:['W'] };
  const selectPhase = async (phase) => {
    setActivePhase(phase);
    // Immediately reflect in the visualizer (no WebSocket roundtrip needed)
    setMetrics(prev => ({
      ...(prev || { queues:{N:0,S:0,E:0,W:0}, vpm:{N:10,S:10,E:10,W:10}, cycle_countdown:30 }),
      green_lights: PHASE_MAP[phase] || ['N','S']
    }));
    try {
      await fetch(`${API_BASE}/api/select-phase`, {
        method: 'POST',         headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
        body: JSON.stringify({ phase })
      });
      addLog('auto', `Phase → ${phase} active`);
    } catch { addLog('error', `Phase ${phase} failed`); }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === "dark-theme" ? "light-theme" : "dark-theme");
  };

  const [mounted, setMounted] = useState(false);
  const [juncCaps, setJuncCaps] = useState({});

  useEffect(() => {
    setMounted(true);
    // Generate static random caps for this session
    const caps = {};
    junctions.forEach(id => caps[id] = Math.floor(Math.random()*20)+80);
    setJuncCaps(caps);
    
    const ws = new WebSocket(`${WS_URL}/ws?api_key=${encodeURIComponent(API_KEY)}`);
    ws.onmessage = (e) => setMetrics(JSON.parse(e.data));
    ws.onerror = () => console.log("WS Error - Presentation Fallback Active.");
    return () => { if(ws.readyState === 1) ws.close(); };
  }, []);

  useEffect(() => {
    document.body.className = theme;
  }, [theme]);

  if (!mounted) return null; // Prevent hydration mismatch

  const addLog = (type, msg) => {
    const time = new Date().toLocaleTimeString();
    setLog(prev => [{ time, type, msg }, ...prev].slice(0, 20));
  };

  const handleAction = async (endpoint, body) => {
    try {
      await fetch(`${API_BASE}/api/${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      addLog("auto", `Executing mandate: ${endpoint} -> ${selectedNode}`);
    } catch { addLog("error", "Link integrity 0% - Checking backups."); }
  };

  const renderView = () => {
    switch(activeTab) {
      case 'map': return <CityMap metrics={metrics} selectedNode={selectedNode} setSelectedNode={setSelectedNode} />;
      case 'network': return (
        <div className="grid grid-cols-2 gap-6 flex-1 p-8">
          <div className="glass-card p-12 flex-center shadow-xl"><h3>NODE TOPOLOGY</h3><p className="text-secondary mt-4 font-bold">20/20 CLUSTERS SECURE</p></div>
          <div className="glass-card p-12 flex-center shadow-xl"><h3>DATA LATENCY</h3><p className="text-primary mt-4 font-bold">3.8ms (REAL-TIME)</p></div>
        </div>
      );
      case 'settings': return (
        <div className="glass-card p-12 flex-center flex-1 m-8">
           <h3 className="hud-title">SYSTEM PREFERENCES</h3>
           <div className="mt-8 grid gap-4 w-full max-w-md">
              <button className="theme-toggle-btn w-full py-4 bg-primary text-white border-none" onClick={toggleTheme}>
                 {theme === 'dark-theme' ? '☀️ SWITCH TO LIGHT MODE' : '🌙 SWITCH TO DARK MODE'}
              </button>
           </div>
        </div>
      );
      default: return (
        <>
          <aside className="glass-card junc-index-list shadow-2xl">
            <div className="p-5 term-label" style={{ borderBottom: '1px solid var(--glass-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
               <span style={{ fontSize: '0.8rem' }}>INTERSECTION FLEET</span>
               <div className="pulse-icon" style={{ width: '8px', height: '8px' }} />
            </div>
            <div className="jlist-container">
              {junctions.map(id => (
                <div key={id} className={`jlist-item ${selectedNode === id ? 'active' : ''}`} onClick={() => setSelectedNode(id)}>
                  <span>{id}</span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--secondary)', fontWeight: 800 }}>{juncCaps[id] || '92'}%</span>
                </div>
              ))}
            </div>
          </aside>
          
          <main className="glass-card flex-1 flex flex-col items-center justify-center relative overflow-hidden mx-6 shadow-2xl">
             <div className="absolute top-6 left-6 term-label" style={{ background: 'var(--primary-glow)', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--primary)', fontSize: '0.7rem' }}>
                TACTICAL_STREAM: <span className="text-white">{selectedNode}</span>
             </div>
             <JunctionVisualizer metrics={metrics} size="100%" />
          </main>

          <aside className="glass-card controller-panel shadow-2xl" style={{ overflowY: 'auto' }}>
            <h2 className="hud-title" style={{ fontSize: '1rem', marginBottom: '16px', color: 'var(--text-main)' }}>COMMAND_{selectedNode}</h2>
            
            {/* Mode Toggle — wired to /api/controller-config */}
            <div className="ctrl-mode-toggle" style={{ height: '44px' }}>
              {['manual', 'auto', 'rr'].map(m => (
                <button key={m} className={`ctrl-mode-btn ${ctrlMode === m ? `active-${m}` : ''}`}
                  style={{ fontSize: '0.75rem' }}
                  onClick={async () => {
                    setCtrlMode(m);
                    try {
                      await fetch(`${API_BASE}/api/controller-config`, {
                        method: 'POST',         headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
                        body: JSON.stringify({ mode: m })
                      });
                      addLog('auto', `Mode set → ${m.toUpperCase()}`);
                    } catch { addLog('error', 'Mode switch failed — backend unreachable'); }
                  }}
                >{m.toUpperCase()}</button>
              ))}
            </div>

            {/* Phase Select — NS / EW corridors + individual lanes */}
            <div style={{ marginTop: '14px' }}>
              <div className="term-label" style={{ fontSize: '0.6rem', marginBottom: '8px', color: 'var(--text-dim)' }}>PHASE SELECT</div>
              {/* Corridor pair buttons */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                {[
                  { phase: 'NS', label: '↕ NS CORRIDOR', color: 'var(--primary)' },
                  { phase: 'EW', label: '↔ EW CORRIDOR', color: 'var(--secondary)' },
                ].map(({ phase, label, color }) => (
                  <button key={phase} id={`phase-${phase}-btn`}
                    className="theme-toggle-btn"
                    style={{ height: '40px', fontSize: '0.7rem', fontWeight: 800, justifyContent: 'center',
                      border: `2px solid ${color}`, color: color, borderRadius: '8px',
                      background: activePhase === phase ? `${color}22` : 'transparent',
                      boxShadow: activePhase === phase ? `0 0 12px ${color}88` : 'none',
                      transition: 'all 0.2s' }}
                    onClick={() => selectPhase(phase)}
                  >{label}</button>
                ))}
              </div>
              {/* Individual lane buttons */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
                {['N','S','E','W'].map(d => (
                  <button key={d} id={`phase-${d}-btn`}
                    className="theme-toggle-btn"
                    style={{ height: '34px', fontSize: '0.75rem', fontWeight: 900, justifyContent: 'center',
                      border: '1px solid var(--glass-border)', borderRadius: '6px',
                      background: activePhase === d ? 'var(--primary-glow)' : 'transparent',
                      color: activePhase === d ? 'var(--primary)' : 'var(--text-dim)',
                      transition: 'all 0.2s' }}
                    onClick={() => selectPhase(d)}
                  >{d}</button>
                ))}
              </div>
            </div>

            {/* 4-Direction VPM Inputs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '16px' }}>
              {['N','S','E','W'].map(l => (
                <div key={l} className="vps-vessel" style={{ padding: '10px' }}>
                  <label className="term-label" style={{ fontSize: '0.65rem', marginBottom: '6px' }}>LANE {l} VPM</label>
                  <input type="number" min="1" max="120" value={vps[l] ?? 10}
                    onChange={e => setVps({...vps, [l]: Number(e.target.value)})}
                    className="vps-field" style={{ fontSize: '1.3rem', width: '100%' }} />
                </div>
              ))}
            </div>

            {/* Phase Duration Input */}
            <div className="vps-vessel" style={{ padding: '10px', marginTop: '10px' }}>
              <label className="term-label" style={{ fontSize: '0.65rem', marginBottom: '6px' }}>PHASE DURATION (s)</label>
              <input type="number" min="10" max="300" value={phaseDuration}
                onChange={e => setPhaseDuration(Number(e.target.value))}
                className="vps-field" style={{ fontSize: '1.3rem', width: '100%', textAlign: 'center' }} />
            </div>

            {/* Apply VPM & Duration — wired to /api/controller-config */}
            <button id="apply-vpm-btn" className="theme-toggle-btn mt-4 w-full"
              style={{ background: 'var(--primary)', color: 'white', border: 'none', height: '44px', justifyContent: 'center', fontSize: '0.85rem', fontWeight: 800, borderRadius: '10px' }}
              onClick={async () => {
                try {
                  await fetch(`${API_BASE}/api/controller-config`, {
                    method: 'POST',         headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
                    body: JSON.stringify({ mode: ctrlMode, vps: vps, duration: phaseDuration })
                  });
                  addLog('auto', `Config applied → VPM N:${vps.N} S:${vps.S} E:${vps.E} W:${vps.W} | T:${phaseDuration}s`);
                } catch { addLog('error', 'Apply failed — backend unreachable'); }
              }}
            >✅ APPLY CONFIG</button>

            {/* Emergency Trigger */}
            <button id="emergency-btn-main" className="theme-toggle-btn mt-3 w-full"
              style={{ background: 'var(--accent)', color: 'white', border: 'none', height: '52px', justifyContent: 'center', fontSize: '1rem', fontWeight: 800, borderRadius: '12px', boxShadow: '0 8px 24px rgba(244, 63, 94, 0.4)' }}
              onClick={async () => {
                try {
                  await fetch(`${API_BASE}/api/emergency/request`, {
                    method: 'POST',         headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
                    body: JSON.stringify({ zone: selectedNode, start: selectedNode, end: 'INT_001', device_id: 'DASHBOARD' })
                  });
                  addLog('error', `🚨 EMERGENCY activated for ${selectedNode}`);
                } catch { addLog('error', 'Emergency trigger failed'); }
              }}
            >🚨 TRIGGER EMERGENCY</button>

            {/* Clear Emergency */}
            <button id="clear-emergency-btn" className="theme-toggle-btn mt-2 w-full"
              style={{ border: '1px solid var(--text-dim)', height: '36px', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, borderRadius: '8px', color: 'var(--text-dim)' }}
              onClick={async () => {
                try {
                  await fetch(`${API_BASE}/api/emergency/clear`, { method: 'POST' });
                  addLog('auto', 'Emergency cleared — resuming AI control');
                } catch { addLog('error', 'Clear emergency failed'); }
              }}
            >✖ CLEAR EMERGENCY</button>

            {/* AI Advisory */}
            <div className="mt-4 p-4 glass-card" style={{ background: 'rgba(0,0,0,0.03)', border: '1px dashed var(--primary)' }}>
               <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                 <div className="term-label" style={{ color: 'var(--primary)', fontSize: '0.65rem' }}>AI_PILOT_ADVISORY (SLM)</div>
                 <button onClick={async () => {
                   setSlmThinking(true);
                   try {
                     const res = await fetch(`${API_BASE}/api/slm-analyze?zone=${selectedNode}`);
                     const data = await res.json();
                     if(data.status === "success") {
                       setSlmAdvisory(data.data);
                       addLog('auto', `SLM Intelligence updated for ${selectedNode}`);
                     } else {
                       throw new Error(data.message);
                     }
                   } catch(e) {
                     addLog('error', `SLM Error: ${e.message}`);
                     setSlmAdvisory({ reasoning: "Failed to reach SLM.", recommendation: "Check backend logs." });
                   }
                   setSlmThinking(false);
                 }} 
                 disabled={slmThinking}
                 style={{ background: 'var(--primary-glow)', color: 'var(--primary)', border: '1px solid var(--primary)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.6rem', cursor: 'pointer' }}>
                   {slmThinking ? "ANALYZING..." : "🧠 GET ANALYSIS"}
                 </button>
               </div>
               <p style={{ fontSize: '0.75rem', marginTop: '10px', lineHeight: '1.6', color: 'var(--text-dim)' }}>
                 {slmThinking ? (
                   <span style={{ color: 'var(--primary)' }} className="pulse-anim">Running tactical heuristics and neural simulation...</span>
                 ) : (
                   <>
                     <strong>Reasoning:</strong> {slmAdvisory.reasoning}<br/>
                     {slmAdvisory.recommendation && (
                       <span style={{ color: 'var(--toast-success)' }}><strong>Recommendation:</strong> {slmAdvisory.recommendation}</span>
                     )}
                   </>
                 )}
               </p>
            </div>
          </aside>
        </>
      );
    }
  };

  return (
    <div className={`dashboard-app-container ${theme}`} id="dashboard-root">
      <div className="scanline-overlay" />
      
      <aside className="sidebar-v3">
        <div className="sidebar-logo" style={{ fontSize: '1.8rem', marginBottom: '40px', filter: 'drop-shadow(0 0 12px var(--primary))' }}>🚥</div>
        {['junction', 'network', 'map', 'settings'].map(id => (
          <button key={id} 
            className={`sidebar-btn ${activeTab === id ? 'active' : ''}`} 
            onClick={() => setActiveTab(id)}
            data-testid={`sidebar-${id}`}>
            <span style={{ fontSize: '1.3rem' }}>{id === 'junction' ? '📊' : id === 'network' ? '🌐' : id === 'map' ? '🗺️' : '⚙️'}</span>
          </button>
        ))}
        <div style={{ marginTop: 'auto' }}>
           <button id="global-theme-toggle" className="sidebar-btn" style={{ background: 'var(--glass-border)' }} onClick={toggleTheme} title="TOGGLE THEME">
             <span style={{ fontSize: '1.3rem' }}>{theme === "dark-theme" ? "🌞" : "🌙"}</span>
           </button>
        </div>
      </aside>

      <main className="dashboard-v3-theater">
        <header className="tactical-header-v3" style={{ height: '80px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <h1 className="hud-title" style={{ fontSize: '1.4rem' }}>DAITFO — MISSION CONTROL</h1>
            <div className="badge-v3" style={{ border: '1px solid var(--primary)', color: 'var(--primary)', background: 'var(--primary-glow)', padding: '6px 14px' }}>OPERATIONAL</div>
          </div>
          <div className="header-badges" style={{ gap: '20px' }}>
             <div className="badge-v3" style={{ padding: '8px 16px' }}>FLOW: 1.48k/m</div>
             <div className="badge-v3" style={{ padding: '8px 16px', color: 'var(--secondary)', borderColor: 'var(--secondary)' }}>GRID_HEALTH: 98%</div>
             <div className="phase-clock-v3" style={{ padding: '8px 20px', fontSize: '1rem' }}>PHASE TIC: {metrics?.cycle_countdown ?? 12}S</div>
             <button id="header-theme-toggle" className="theme-toggle-btn" style={{ padding: '8px 16px' }} onClick={toggleTheme}>THEME: {theme === 'dark-theme' ? 'DARK' : 'LIGHT'}</button>
          </div>
        </header>
        
        <div className="main-viewport" style={{ padding: '24px' }}>
          {renderView()}
        </div>

        <footer className="bottom-terminal" style={{ height: '180px' }}>
          <section className="term-section" style={{ flex: 1.4 }}>
            <div className="term-label" style={{ fontSize: '0.75rem' }}>COMMAND LOG FEED</div>
            <div className="log-feed" style={{ marginTop: '12px' }}>
              {log.length === 0 ? (
                <>
                  <div className="log-entry" style={{ opacity: 0.5 }}>[09:55:01] System boot verified.</div>
                  <div className="log-entry" style={{ opacity: 0.7 }}>[09:55:04] All nodes (20/20) operational.</div>
                  <div className="log-entry" style={{ color: 'var(--primary)' }}>[09:55:08] Cluster Alpha under AI oversight.</div>
                </>
              ) : log.map((e, i) => (
                <div key={i} className={`log-entry ${e.type}`}>[{e.time}] {e.msg}</div>
              ))}
            </div>
          </section>
          <section className="term-section" style={{ flex: 1.8 }}>
            <div className="term-label" style={{ fontSize: '0.75rem' }}>GRID THROUGHPUT ANALYTICS</div>
            <div className="flex-1 flex items-end gap-1 px-4 mt-4">
               {Array.from({length: 50}).map((_, i) => {
                 const h = 10 + Math.sin(i * 0.25) * 40 + (mounted ? Math.random() * 50 : 20);
                 return (
                   <div key={i} style={{ 
                     height: `${h}%`, 
                     width: '100%', 
                     background: 'linear-gradient(to top, var(--primary), var(--secondary))', 
                     opacity: 0.3 + (i/50)*0.7,
                     borderRadius: '4px 4px 0 0',
                     transition: 'height 0.8s cubic-bezier(0.4, 0, 0.2, 1)'
                   }} />
                 );
               })}
            </div>
          </section>
          <section className="term-section">
             <div className="term-label" style={{ fontSize: '0.75rem' }}>SYSTEM VITALITY</div>
             <div className="flex-1 flex flex-col justify-center gap-4">
                <div style={{ fontSize: '0.8rem' }}>
                  <div className="flex justify-between mb-2"><span>EDGE COMPUTE</span><span className="text-cyan">18.4%</span></div>
                  <div style={{ height: '6px', background: 'var(--glass-border)', borderRadius: '3px', overflow: 'hidden' }}><div style={{ width: '18%', height: '100%', background: 'var(--primary)', boxShadow: '0 0 15px var(--primary)' }} /></div>
                </div>
                <div style={{ fontSize: '0.8rem' }}>
                  <div className="flex justify-between mb-2"><span>NETWORK UPLINK</span><span className="text-secondary">91.2%</span></div>
                  <div style={{ height: '6px', background: 'var(--glass-border)', borderRadius: '3px', overflow: 'hidden' }}><div style={{ width: '91%', height: '100%', background: 'var(--secondary)', boxShadow: '0 0 15px var(--secondary)' }} /></div>
                </div>
             </div>
          </section>
        </footer>
      </main>
      
      <style jsx>{`
        .flex { display: flex; }
        .flex-col { flex-direction: column; }
        .justify-center { justify-content: center; }
        .justify-between { justify-content: space-between; }
        .items-center { align-items: center; }
        .items-end { align-items: flex-end; }
        .flex-center { display: flex; align-items: center; justify-content: center; text-align: center; }
        .shadow-2xl { box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important; }
        .shadow-xl { box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3) !important; }
      `}</style>
    </div>
  );
}
