"use client";

import { useState } from "react";
import { Database, TrendingUp, Cpu, Play, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export default function ControlPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [days, setDays] = useState(365);
  const [sandboxDays, setSandboxDays] = useState(10);
  const [capital, setCapital] = useState(1000000);

  const triggerTask = async (taskName: string, endpoint: string, body?: any) => {
    setLoading(taskName);
    setMessage(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const response = await fetch(`${baseUrl}/system/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Task failed");

      setMessage({ type: "success", text: data.message });
      // Reload page to reflect new data
      if (taskName === "sandbox") {
        setTimeout(() => window.location.reload(), 1500);
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="glass-card mb-8">
      <h2 style={{ fontSize: "20px", marginBottom: "20px" }}>System Controls</h2>

      {message && (
        <div 
          className="mb-6 p-4 rounded flex items-center gap-3" 
          style={{ 
            background: message.type === "success" ? "rgba(40, 167, 69, 0.1)" : "rgba(220, 53, 69, 0.1)",
            border: `1px solid ${message.type === "success" ? "var(--success)" : "var(--danger)"}`,
            color: message.type === "success" ? "var(--success)" : "var(--danger)"
          }}
        >
          {message.type === "success" ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
          {message.text}
        </div>
      )}

      <div className="grid gap-6" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))" }}>
        {/* Seed Database */}
        <div className="p-4 rounded" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)" }}>
          <div className="flex items-center gap-3 mb-4 text-primary">
            <Database size={24} />
            <h3 style={{ fontSize: "16px", margin: 0 }}>Initialize DB</h3>
          </div>
          <p className="text-muted mb-4" style={{ fontSize: "14px", height: "40px" }}>Seed the database with the default top 20 stocks.</p>
          <button 
            className="btn-primary w-full flex justify-center items-center gap-2"
            disabled={!!loading}
            onClick={() => triggerTask("seed", "seed")}
          >
            {loading === "seed" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Seed Database
          </button>
        </div>

        {/* Fetch Prices */}
        <div className="p-4 rounded" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)" }}>
          <div className="flex items-center gap-3 mb-4 text-warning">
            <TrendingUp size={24} />
            <h3 style={{ fontSize: "16px", margin: 0 }}>Fetch Prices</h3>
          </div>
          <p className="text-muted mb-4" style={{ fontSize: "14px", height: "40px" }}>Download historical OHLCV data from Yahoo Finance.</p>
          <div className="flex gap-2 mb-4">
            <input 
              type="number" 
              value={days} 
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-transparent border rounded p-2 text-white w-full"
              style={{ borderColor: "var(--border-color)" }}
              min="1"
            />
            <span className="text-muted flex items-center">days</span>
          </div>
          <button 
            className="btn-primary w-full flex justify-center items-center gap-2"
            disabled={!!loading}
            onClick={() => triggerTask("fetch", "fetch-prices", { days, full: false })}
            style={{ background: "var(--warning)" }}
          >
            {loading === "fetch" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Fetch Data
          </button>
        </div>

        {/* Run Agents */}
        <div className="p-4 rounded" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)" }}>
          <div className="flex items-center gap-3 mb-4" style={{ color: "var(--accent)" }}>
            <Cpu size={24} />
            <h3 style={{ fontSize: "16px", margin: 0 }}>Run AI Agents</h3>
          </div>
          <p className="text-muted mb-4" style={{ fontSize: "14px", height: "40px" }}>Execute LLM agents to fetch news and score stocks.</p>
          <button 
            className="btn-primary w-full flex justify-center items-center gap-2"
            disabled={!!loading}
            onClick={() => triggerTask("agents", "run-agents")}
            style={{ background: "var(--accent)", marginTop: "auto" }}
          >
            {loading === "agents" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Run Predictions
          </button>
        </div>

        {/* Run Sandbox */}
        <div className="p-4 rounded" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)" }}>
          <div className="flex items-center gap-3 mb-4 text-success">
            <TrendingUp size={24} />
            <h3 style={{ fontSize: "16px", margin: 0 }}>Run Sandbox</h3>
          </div>
          <p className="text-muted mb-4" style={{ fontSize: "14px", height: "40px" }}>Simulate trading over past predictions.</p>
          <div className="flex gap-2 mb-4">
            <input 
              type="number" 
              value={sandboxDays} 
              onChange={(e) => setSandboxDays(Number(e.target.value))}
              className="bg-transparent border rounded p-2 text-white w-1/2"
              style={{ borderColor: "var(--border-color)" }}
              min="1"
              title="Days"
            />
            <input 
              type="number" 
              value={capital} 
              onChange={(e) => setCapital(Number(e.target.value))}
              className="bg-transparent border rounded p-2 text-white w-1/2"
              style={{ borderColor: "var(--border-color)" }}
              min="1000"
              title="Initial Capital"
            />
          </div>
          <button 
            className="btn-primary w-full flex justify-center items-center gap-2"
            disabled={!!loading}
            onClick={() => triggerTask("sandbox", "sandbox", { days: sandboxDays, capital })}
            style={{ background: "var(--success)" }}
          >
            {loading === "sandbox" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Simulate
          </button>
        </div>
      </div>
    </div>
  );
}
