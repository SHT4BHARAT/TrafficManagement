"use client";
import React, { useState, useEffect } from "react";

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

  const handleSend = () => {
    if (!query) return;
    setChat([...chat, { role: "user", content: query }]);
    // Mock response logic
    setTimeout(() => {
      setChat(prev => [...prev, { 
        role: "assistant", 
        content: `Analyzing ${query}... Detection shows E-W corridor pressure at INT_001. I recommend increasing E-W Green duration by 15%.` 
      }]);
    }, 1000);
    setQuery("");
  };

  return (
    <div className="dashboard-container">
      {/* Sidebar / Branding */}
      <header className="main-header glass-panel">
        <h1 className="gradient-text">DAITFO v2.0</h1>
        <div className="status-badge glow-text">SYSTEM SECURE (mTLS)</div>
      </header>

      <div className="content-grid">
        {/* Metric Cards */}
        <div className="metrics-group">
          <div className="metric-card glass-panel">
            <h3>Intersection Control</h3>
            <p className="big-value">{metrics?.intersection || "Loading..."}</p>
            <span className="status-indicator success">{metrics?.mode}</span>
          </div>
          
          <div className="metric-card glass-panel">
            <h3>Flow Efficiency</h3>
            <p className="big-value reward">{metrics?.reward || "0"}</p>
            <span className="unit">NET_QUEUE_GAIN</span>
          </div>

          <div className="metric-card glass-panel">
            <h3>System Health</h3>
            <p className="big-value">{metrics?.uptime}</p>
            <span className="status-indicator">Latency: 4ms</span>
          </div>
        </div>

        {/* Real-time Visualization Mock */}
        <div className="viz-panel glass-panel">
          <div className="viz-header">
            <h3>Live Lane Analytics</h3>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Real-time Stream</span>
              <div className="pulse-icon"></div>
            </div>
          </div>
          <div className="viz-container">
            {metrics && Object.entries(metrics.queues).map(([key, val]) => (
              <div key={key} className="lane-analytics-row">
                <div className="lane-info">
                  <span className="lane-label">ZONE {key}</span>
                  <span className={`lane-status ${val > 20 ? 'alert' : 'optimal'}`}>
                    {val > 20 ? '!! CONGESTED' : 'OPTIMAL'}
                  </span>
                </div>
                <div className="bar-wrapper">
                  <div className="bar-bg">
                    <div 
                      className="bar-fill" 
                      style={{ 
                        width: `${Math.min((val / 30) * 100, 100)}%`, 
                        background: val > 20 ? 'linear-gradient(90deg, #ff4b2b, #ff416c)' : 'linear-gradient(90deg, #00f2fe, #4facfe)' 
                      }}
                    >
                      <div className="bar-shimmer"></div>
                    </div>
                  </div>
                  <span className="lane-val">{val} <small>vph</small></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* HQ Assistant Chat */}
        <div className="chat-panel glass-panel">
          <h3>IQ Assistant (Local LLM)</h3>
          <div className="chat-history">
            {chat.map((msg, idx) => (
              <div key={idx} className={`chat-bubble ${msg.role}`}>
                <span className="role-tag">{msg.role === 'assistant' ? 'AI' : 'OPERATOR'}</span>
                <p>{msg.content}</p>
              </div>
            ))}
          </div>
          <div className="chat-input-area">
            <input 
              type="text" 
              placeholder="Query system status..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={handleSend} className="btn-primary">SEND</button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .dashboard-container {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 24px;
          max-width: 1400px;
          margin: 0 auto;
        }

        .main-header {
          padding: 16px 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .main-header h1 {
          font-size: 1.5rem;
          letter-spacing: 2px;
          font-weight: 700;
        }

        .status-badge {
          font-size: 0.8rem;
          padding: 4px 12px;
          border: 1px solid var(--success);
          color: var(--success);
          border-radius: 20px;
        }

        .content-grid {
          display: grid;
          grid-template-columns: 1fr 340px;
          grid-template-rows: auto 1fr;
          gap: 24px;
        }

        .metrics-group {
          grid-column: 1 / 3;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }

        .metric-card {
          padding: 24px;
        }

        .big-value {
          font-size: 2rem;
          font-weight: 600;
          margin: 8px 0;
        }

        .reward {
          color: var(--success);
        }

        .viz-panel {
          padding: 24px;
          min-height: 400px;
        }

        .viz-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .lane-analytics-row {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .lane-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .lane-label {
          font-size: 0.7rem;
          font-weight: 800;
          color: var(--text-secondary);
          letter-spacing: 1px;
        }

        .lane-status {
          font-size: 0.65rem;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 4px;
        }

        .lane-status.optimal {
          background: rgba(0, 242, 254, 0.1);
          color: var(--primary);
        }

        .lane-status.alert {
          background: rgba(255, 75, 43, 0.1);
          color: #ff4b2b;
          animation: blink 1s infinite;
        }

        .bar-wrapper {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .bar-bg {
          flex: 1;
          height: 8px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 4px;
          overflow: hidden;
          position: relative;
        }

        .bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
          position: relative;
        }

        .bar-shimmer {
          position: absolute;
          top: 0;
          left: 0;
          width: 50%;
          height: 100%;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.2),
            transparent
          );
          animation: shimmer 2s infinite;
        }

        .lane-val {
          font-size: 1rem;
          font-weight: 700;
          min-width: 60px;
          text-align: right;
        }

        .lane-val small {
          font-size: 0.6rem;
          opacity: 0.4;
          margin-left: 2px;
        }

        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }

        @keyframes blink {
          50% { opacity: 0.5; }
        }

        .chat-input-area {
          margin-top: auto;
          display: flex;
          gap: 12px;
        }

        input {
          flex: 1;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--glass-border);
          padding: 12px 18px;
          border-radius: 12px;
          color: white;
          outline: none;
          transition: all 0.3s;
        }

        input:focus {
          border-color: var(--primary);
          background: rgba(255, 255, 255, 0.08);
          box-shadow: 0 0 15px rgba(0, 242, 254, 0.1);
        }

        .btn-primary {
          background: linear-gradient(135deg, var(--primary), #4facfe);
          border: none;
          padding: 0 24px;
          border-radius: 12px;
          color: white;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 5px 15px rgba(0, 242, 254, 0.3);
        }

        @keyframes pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.5); opacity: 0.5; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
