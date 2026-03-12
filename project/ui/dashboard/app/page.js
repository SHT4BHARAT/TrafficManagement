"use client";
import React, { useState, useEffect } from "react";

// 2D Digital Twin Junction Component
const JunctionVisualizer = ({ metrics }) => {
  const lanes = ['N', 'S', 'E', 'W'];
  
  if (!metrics) {
    return (
      <div className="junction-box loading">
        <div className="flex-center flex-col gap-2">
          <div className="pulse-icon large"></div>
          <span className="loading-text">SYNCHRONIZING DIGITAL TWIN...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="junction-box">
      <svg viewBox="0 0 200 200" className="junction-svg">
        {/* Road Structure */}
        <rect x="80" y="0" width="40" height="200" fill="#1e293b" />
        <rect x="0" y="80" width="200" height="40" fill="#1e293b" />
        
        {/* Lane Markings */}
        <line x1="100" y1="0" x2="100" y2="70" stroke="#475569" strokeDasharray="4" />
        <line x1="100" y1="130" x2="100" y2="200" stroke="#475569" strokeDasharray="4" />
        <line x1="0" y1="100" x2="70" y2="100" stroke="#475569" strokeDasharray="4" />
        <line x1="130" y1="100" x2="200" y2="100" stroke="#475569" strokeDasharray="4" />

        {/* Traffic Lights */}
        {lanes.map(lane => {
          const isGreen = metrics?.green_lights?.includes(lane);
          let pos = {};
          if(lane === 'N') pos = { x: 70, y: 70 };
          if(lane === 'S') pos = { x: 120, y: 120 };
          if(lane === 'E') pos = { x: 120, y: 70 };
          if(lane === 'W') pos = { x: 70, y: 120 };
          
          return (
            <circle 
              key={lane}
              cx={pos.x} cy={pos.y} r="4.5" 
              fill={isGreen ? '#22c55e' : '#ef4444'} 
              className={isGreen ? 'pulse-green' : ''}
              style={{ filter: isGreen ? 'drop-shadow(0 0 6px #22c55e)' : 'none' }}
            />
          );
        })}

        {/* Dynamic Traffic Dots (Simulated) */}
        {lanes.map(lane => {
          const density = metrics?.queues?.[lane] || 0;
          const dotsCount = Math.ceil(density / 2); // More dots
          const dots = Array.from({ length: dotsCount });

          return dots.map((_, i) => {
            let startPos = { x: 0, y: 0 };
            if(lane === 'N') startPos = { x: 90, y: -10 };
            if(lane === 'S') startPos = { x: 110, y: 210 };
            if(lane === 'E') startPos = { x: 210, y: 90 };
            if(lane === 'W') startPos = { x: -10, y: 110 };

            return (
              <circle 
                key={`${lane}-${i}`}
                cx={startPos.x} 
                cy={startPos.y} 
                r="2.8"
                fill="#fbbf24"
                className={`traffic-dot dot-${lane.toLowerCase()}`}
                style={{ 
                  animationDelay: `${i * (5/Math.max(1, dotsCount))}s`,
                  animationDuration: `${Math.max(2, 6 - (density/5))}s`,
                  filter: 'drop-shadow(0 0 3px rgba(251, 191, 36, 0.9))'
                }}
              />
            );
          });
        })}

        {/* Intersection Core */}
        <rect x="80" y="80" width="40" height="40" fill="#334155" />
      </svg>
      
      <div className="visualizer-legend">
        <span className="legend-item"><span className="dot green"></span> GREEN</span>
        <span className="legend-item"><span className="dot red"></span> RED</span>
        <span className="legend-item"><span className="dot yellow"></span> VEHICLE</span>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [query, setQuery] = useState("");
  const [chat, setChat] = useState([
    { role: "assistant", content: "System initialized. How can I assist you today, Operator?" }
  ]);

  useEffect(() => {
    // Real-time WebSocket connection
    const socket = new WebSocket("ws://localhost:8000/ws");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics(data);
    };

    socket.onopen = () => console.log("[WS] Dashboard connected to backend");
    socket.onclose = () => console.log("[WS] Dashboard disconnected");

    return () => socket.close();
  }, []);

  const handleSend = async () => {
    if (!query.trim()) return;
    const userMsg = { role: "user", content: query };
    setChat(prev => [...prev, userMsg]);
    
    // Add temporary loading bubble
    setChat(prev => [...prev, { role: "assistant", content: "Thinking..." }]);

    try {
      const response = await fetch("http://localhost:8000/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });
      const data = await response.json();
      
      // Replace loading bubble with real answer
      setChat(prev => {
        const newChat = [...prev];
        newChat[newChat.length - 1] = { role: "assistant", content: data.answer };
        return newChat;
      });
    } catch (err) {
      setChat(prev => {
        const newChat = [...prev];
        newChat[newChat.length - 1] = { 
          role: "assistant", 
          content: "Connection Error: Is the local LLM backend running on port 8000?" 
        };
        return newChat;
      });
    }
    setQuery("");
  };

  return (
    <div className="dashboard-shell">
      {/* 1. COMMAND SIDEBAR */}
      <aside className="command-sidebar">
        <div className="side-icon glow-primary">🛰️</div>
        <div className="side-icon">🚦</div>
        <div className="side-icon">🗺️</div>
        <div className="side-icon">⚙️</div>
        <div style={{ marginTop: 'auto' }} className="side-icon">👤</div>
      </aside>

      {/* 2. MAIN TELEMETRY & TACTICAL MAP */}
      <main className="main-theater">
        <header className="hud-header">
          <div className="flex-col">
            <h1 className="hud-title">DAITFO Command Center</h1>
            <p className="text-cyan" style={{ fontSize: '0.7rem', letterSpacing: '2px', fontWeight: 'bold' }}>
              TRANSIT OPTIMIZATION ENGINE v2.0
            </p>
          </div>
          <div className="glass-card" style={{ padding: '8px 20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="live-tag pulse" style={{ color: 'var(--secondary)', fontSize: '0.7rem' }}>● AI_ACTUATED</span>
            <div className="stat-label" style={{ borderLeft: '1px solid var(--glass-border)', paddingLeft: '12px' }}>
              MTLS_SECURE: <span className="text-cyan">VALID</span>
            </div>
          </div>
        </header>

        {/* Global Telemetry Card */}
        <section className="glass-card" style={{ padding: '24px' }}>
          <div className="telemetry-grid">
            <div className="stat-vessel">
              <span className="stat-label">SYSTEM UPTIME</span>
              <div className="stat-value">{metrics?.uptime || "99.9%"}</div>
              <div className="text-emerald" style={{ fontSize: '0.6rem' }}>STABLE_NODE: 0x4F2A</div>
            </div>
            <div className="stat-vessel">
              <span className="stat-label">FLOW EFFICIENCY</span>
              <div className="stat-value text-cyan">+{metrics?.reward || "0"}</div>
              <div className="stat-label">REWARD_COEFFICIENT</div>
            </div>
            <div className="stat-vessel">
              <span className="stat-label">INTERSECTION_ID</span>
              <div className="stat-value" style={{ fontSize: '1.2rem' }}>{metrics?.intersection || "INT_001_HQ"}</div>
              <div className="text-cyan" style={{ fontSize: '0.6rem' }}>LATENCY: 4ms</div>
            </div>
          </div>

          <div className="tactical-map">
            <div className="map-container">
              <div className="map-scan-line"></div>
              <JunctionVisualizer metrics={metrics} />
            </div>
            <div className="visualizer-legend" style={{ marginTop: '24px' }}>
              <div className="legend-item"><span className="dot" style={{ background: 'var(--secondary)' }}></span> GREEN</div>
              <div className="legend-item"><span className="dot" style={{ background: 'var(--accent)' }}></span> RED</div>
              <div className="legend-item"><span className="dot" style={{ background: '#fbbf24' }}></span> VEHICLE</div>
            </div>
          </div>
        </section>

        {/* Zone Analytics Cards */}
        <section className="zone-grid">
          {metrics?.queues && Object.entries(metrics.queues).map(([lane, val]) => (
            <div key={lane} className={`glass-card zone-card ${metrics?.emergency?.active && metrics?.emergency?.zone === lane ? 'heavy' : (val > 15 ? 'heavy' : 'active')}`} style={{ padding: '20px' }}>
              <div className="flex justify-between items-center" style={{ marginBottom: '12px' }}>
                <span className="stat-label">SECTOR_{lane}</span>
                <span className="text-cyan" style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{val} VPS</span>
              </div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ 
                  height: '100%', 
                  width: `${Math.min((val / 30) * 100, 100)}%`,
                  background: val > 15 ? 'var(--accent)' : 'var(--primary)',
                  boxShadow: `0 0 10px ${val > 15 ? 'var(--accent)' : 'var(--primary)'}`
                }}></div>
              </div>
              <div className="flex justify-between items-center" style={{ marginTop: '12px', fontSize: '0.7rem' }}>
                <span className="stat-label">ACTUATED: {metrics.timings?.[lane] || 45}s</span>
                {metrics?.emergency?.active && metrics?.emergency?.zone === lane && (
                  <span className="text-rose" style={{ fontWeight: 'bold' }}>GREEN_CORRIDOR_LOCK</span>
                )}
              </div>
            </div>
          ))}
        </section>
      </main>

      {/* 3. ASSISTANT WING */}
      <aside className="assistant-wing">
        <div style={{ padding: '24px', borderBottom: '1px solid var(--glass-border)' }}>
          <h3 className="hud-title" style={{ fontSize: '0.9rem' }}>IQ_ASSISTANT</h3>
          <p className="stat-label">LOCAL_LLM OVERRIDE_ACTIVE</p>
        </div>
        
        <div className="chat-history" style={{ padding: '24px' }}>
          {chat.map((msg, idx) => (
            <div key={idx} className={`chat-bubble ${msg.role}`} style={{ 
              background: msg.role === 'assistant' ? 'rgba(6, 249, 249, 0.05)' : 'rgba(255,255,255,0.02)',
              borderLeft: msg.role === 'assistant' ? '2px solid var(--primary)' : 'none',
              borderRight: msg.role === 'user' ? '2px solid rgba(255,255,255,0.2)' : 'none',
              marginBottom: '16px',
              padding: '12px',
              borderRadius: '8px'
            }}>
              <span className="role-tag" style={{ fontSize: '0.5rem', opacity: 0.5 }}>{msg.role.toUpperCase()}</span>
              <p style={{ fontSize: '0.85rem', lineHeight: '1.4' }}>{msg.content}</p>
            </div>
          ))}
        </div>

        <div style={{ padding: '24px', background: 'rgba(0,0,0,0.2)' }}>
          <div className="chat-input-area" style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '4px' }}>
            <input 
              type="text" 
              placeholder="Query Tactical Data..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              style={{ background: 'transparent', border: 'none', outline: 'none', padding: '12px' }}
            />
            <button onClick={handleSend} className="btn-primary" style={{ padding: '0 16px', background: 'var(--primary)', color: '#000', borderRadius: '6px' }}>
              ▶
            </button>
          </div>
        </div>
      </aside>

      <style jsx>{`
        .side-icon {
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.2rem;
          cursor: pointer;
          opacity: 0.5;
          transition: all 0.3s;
          border-radius: 8px;
        }
        .side-icon:hover {
          opacity: 1;
          background: rgba(6, 249, 249, 0.1);
          color: var(--primary);
        }
        .side-icon.glow-primary {
          opacity: 1;
          color: var(--primary);
          background: rgba(6, 249, 249, 0.1);
        }
      `}</style>
    </div>
  );
}
