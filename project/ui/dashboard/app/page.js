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
            <div className="pulse-icon"></div>
          </div>
          <div className="viz-placeholder">
            {/* Simulation boxes */}
            {metrics && Object.entries(metrics.queues).map(([key, val]) => (
              <div key={key} className="lane-bar">
                <span className="lane-label">{key}</span>
                <div className="bar-bg">
                  <div 
                    className="bar-fill" 
                    style={{ width: `${(val / 30) * 100}%`, background: val > 20 ? 'var(--danger)' : 'var(--primary)' }}
                  ></div>
                </div>
                <span className="lane-val">{val}</span>
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

        .viz-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 32px;
        }

        .lane-bar {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 16px;
        }

        .lane-label { width: 20px; font-weight: 600; }
        .bar-bg { flex: 1; height: 12px; background: rgba(255,255,255,0.05); border-radius: 6px; overflow: hidden; }
        .bar-fill { height: 100%; transition: width 0.5s ease-out; }

        .chat-panel {
          padding: 24px;
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .chat-history {
          flex: 1;
          overflow-y: auto;
          margin: 16px 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .chat-bubble {
          padding: 12px;
          border-radius: 12px;
          font-size: 0.9rem;
          line-height: 1.4;
        }

        .chat-bubble.assistant {
          background: rgba(0, 242, 254, 0.05);
          border-left: 3px solid var(--primary);
        }

        .chat-bubble.user {
          background: rgba(255, 255, 255, 0.05);
          align-self: flex-end;
          border-right: 3px solid var(--text-secondary);
        }

        .role-tag {
          font-size: 0.7rem;
          font-weight: 700;
          display: block;
          margin-bottom: 4px;
          opacity: 0.5;
        }

        .chat-input-area {
          display: flex;
          gap: 12px;
        }

        input {
          flex: 1;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--glass-border);
          padding: 10px 16px;
          border-radius: 8px;
          color: white;
          outline: none;
        }

        .pulse-icon {
          width: 12px;
          height: 12px;
          background: var(--success);
          border-radius: 50%;
          box-shadow: 0 0 10px var(--success);
          animation: pulse 2s infinite;
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
