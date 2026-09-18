"use client";

import { useState, useEffect, useRef } from "react";
import { Database, TrendingUp, Cpu, Play, Loader2, CheckCircle2, AlertCircle, TerminalSquare, X, Square } from "lucide-react";

function TerminalPopup({ endpoint, onClose }: { endpoint: string, onClose: () => void }) {
  const [logs, setLogs] = useState<string>("");
  const [isDone, setIsDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const es = new EventSource(`${baseUrl}/system/${endpoint}`);

    es.onmessage = (event) => {
      if (event.data === "[DONE]") {
        setIsDone(true);
        es.close();
      } else {
        setLogs((prev) => prev + event.data + "\n");
      }
    };

    es.onerror = (err) => {
      console.error("EventSource failed:", err);
      setLogs((prev) => prev + "\n[Connection closed or error occurred]\n");
      setIsDone(true);
      es.close();
    };

    return () => es.close();
  }, [endpoint]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 999999, // Super high z-index to stay above everything
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      padding: '20px'
    }}>
      <div className="animate-fade-in" style={{
        width: '100%',
        maxWidth: '1000px',
        maxHeight: '90vh',
        backgroundColor: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: '12px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Animated Progress Bar (when running) */}
        {!isDone && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '2px',
            width: '100%',
            background: 'rgba(255,255,255,0.1)',
            overflow: 'hidden',
            zIndex: 10
          }}>
            <div style={{
              height: '100%',
              width: '30%',
              background: '#3b82f6',
              boxShadow: '0 0 10px #3b82f6, 0 0 5px #3b82f6',
              animation: 'indeterminate 1.5s infinite linear'
            }} />
          </div>
        )}
        <style dangerouslySetInnerHTML={{__html: `
          @keyframes indeterminate {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(400%); }
          }
        `}} />

        {/* Terminal Header */}
        <div style={{
          backgroundColor: '#161b22',
          padding: '16px 20px',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <TerminalSquare size={20} color="#8b949e" />
            <span style={{ fontFamily: 'monospace', fontSize: '15px', color: '#8b949e', fontWeight: 600 }}>Terminal — {endpoint.split('?')[0]}</span>
          </div>
          
          {isDone ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ color: '#10b981', fontSize: '13px', fontWeight: 500 }}>Completed</span>
              <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer' }}>
                <X size={24} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#3b82f6' }}>
                <Loader2 size={14} className="animate-spin" /> Running...
              </div>
              <button 
                onClick={onClose}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#ef4444',
                  padding: '4px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                <Square size={10} fill="currentColor" /> Cancel
              </button>
            </div>
          )}
        </div>
        
        {/* Terminal Body */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          backgroundColor: '#0d1117',
          color: '#c9d1d9',
          fontFamily: 'monospace',
          fontSize: '14px',
          lineHeight: '1.6'
        }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
            {logs}
          </pre>
          <div ref={bottomRef} />
        </div>
        
        {/* Terminal Footer */}
        {isDone && (
          <div style={{
            backgroundColor: '#161b22',
            padding: '16px 20px',
            borderTop: '1px solid #30363d',
            display: 'flex',
            justifyContent: 'flex-end'
          }}>
            <button 
              onClick={onClose}
              style={{
                padding: '10px 24px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                cursor: 'pointer',
                fontWeight: 600,
                boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)'
              }}
            >
              Close Window
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ControlPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [days, setDays] = useState(365);
  const [sandboxDays, setSandboxDays] = useState(10);
  const [capital, setCapital] = useState(1000000);
  
  // Streaming state
  const [streamEndpoint, setStreamEndpoint] = useState<string | null>(null);

  const triggerPostTask = async (taskName: string, endpoint: string, body?: any) => {
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
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(null);
    }
  };

  const openStream = (endpoint: string) => {
    setStreamEndpoint(endpoint);
  };

  return (
    <>
      {streamEndpoint && (
        <TerminalPopup 
          endpoint={streamEndpoint} 
          onClose={() => setStreamEndpoint(null)} 
        />
      )}

      <div className="glass-card mb-8 p-8" style={{ background: "rgba(20, 20, 30, 0.4)", border: "1px solid rgba(255,255,255,0.05)" }}>
        {message && (
          <div 
            className="mb-8 p-4 rounded-lg flex items-center gap-3 backdrop-blur-md animate-fade-in" 
            style={{ 
              background: message.type === "success" ? "rgba(40, 167, 69, 0.1)" : "rgba(220, 53, 69, 0.1)",
              border: `1px solid ${message.type === "success" ? "rgba(40,167,69,0.3)" : "rgba(220,53,69,0.3)"}`,
              color: message.type === "success" ? "#4ade80" : "#f87171"
            }}
          >
            {message.type === "success" ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
            {message.text}
          </div>
        )}

        <div className="grid gap-6" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
          
          {/* Seed Database */}
          <div className="p-6 rounded-xl flex flex-col transition-all duration-300 hover:-translate-y-1" style={{ background: "linear-gradient(145deg, rgba(37,99,235,0.1) 0%, rgba(0,0,0,0.3) 100%)", border: "1px solid rgba(37,99,235,0.2)" }}>
            <div className="flex items-center gap-3 mb-4 text-blue-400">
              <Database size={24} />
              <h3 style={{ fontSize: "18px", margin: 0, fontWeight: 500 }}>Initialize DB</h3>
            </div>
            <p className="text-gray-400 mb-6 flex-1" style={{ fontSize: "14px", lineHeight: 1.5 }}>
              Seed the database with the default Top 20 Nifty stocks to prepare the environment.
            </p>
            <button 
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-lg text-white font-medium transition-all"
              style={{ background: "rgba(37,99,235,0.8)", boxShadow: "0 4px 14px 0 rgba(37,99,235,0.39)" }}
              disabled={!!loading}
              onClick={() => triggerPostTask("seed", "seed")}
            >
              {loading === "seed" ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
              Seed Database
            </button>
          </div>

          {/* Fetch Prices */}
          <div className="p-6 rounded-xl flex flex-col transition-all duration-300 hover:-translate-y-1" style={{ background: "linear-gradient(145deg, rgba(234,179,8,0.1) 0%, rgba(0,0,0,0.3) 100%)", border: "1px solid rgba(234,179,8,0.2)" }}>
            <div className="flex items-center gap-3 mb-4 text-yellow-400">
              <TrendingUp size={24} />
              <h3 style={{ fontSize: "18px", margin: 0, fontWeight: 500 }}>Fetch Prices</h3>
            </div>
            <p className="text-gray-400 mb-4 flex-1" style={{ fontSize: "14px", lineHeight: 1.5 }}>
              Download daily historical OHLCV data from Yahoo Finance.
            </p>
            <div className="flex gap-3 mb-6 bg-black/30 p-2 rounded-lg border border-white/5">
              <input 
                type="number" 
                value={days} 
                onChange={(e) => setDays(Number(e.target.value))}
                className="bg-transparent text-white w-full outline-none px-2"
                min="1"
              />
              <span className="text-gray-500 pr-2">days</span>
            </div>
            <button 
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-lg text-black font-medium transition-all"
              style={{ background: "rgba(234,179,8,0.9)", boxShadow: "0 4px 14px 0 rgba(234,179,8,0.39)" }}
              onClick={() => openStream(`fetch-prices/stream?days=${days}`)}
            >
              <TerminalSquare size={18} />
              Start & Stream Logs
            </button>
          </div>

          {/* Run Agents (Streaming) */}
          <div className="p-6 rounded-xl flex flex-col transition-all duration-300 hover:-translate-y-1" style={{ background: "linear-gradient(145deg, rgba(168,85,247,0.1) 0%, rgba(0,0,0,0.3) 100%)", border: "1px solid rgba(168,85,247,0.2)" }}>
            <div className="flex items-center gap-3 mb-4 text-purple-400">
              <Cpu size={24} />
              <h3 style={{ fontSize: "18px", margin: 0, fontWeight: 500 }}>Run AI Agents</h3>
            </div>
            <p className="text-gray-400 mb-6 flex-1" style={{ fontSize: "14px", lineHeight: 1.5 }}>
              Execute all LLM agents (News, Social, Technical) to generate predictions.
            </p>
            <button 
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-lg text-white font-medium transition-all"
              style={{ background: "rgba(168,85,247,0.8)", boxShadow: "0 4px 14px 0 rgba(168,85,247,0.39)" }}
              onClick={() => openStream("run-agents/stream")}
            >
              <TerminalSquare size={18} />
              Start & Stream Logs
            </button>
          </div>

          {/* Run Sandbox (Streaming) */}
          <div className="p-6 rounded-xl flex flex-col transition-all duration-300 hover:-translate-y-1" style={{ background: "linear-gradient(145deg, rgba(34,197,94,0.1) 0%, rgba(0,0,0,0.3) 100%)", border: "1px solid rgba(34,197,94,0.2)" }}>
            <div className="flex items-center gap-3 mb-4 text-green-400">
              <TrendingUp size={24} />
              <h3 style={{ fontSize: "18px", margin: 0, fontWeight: 500 }}>Sandbox Simulator</h3>
            </div>
            <p className="text-gray-400 mb-4 flex-1" style={{ fontSize: "14px", lineHeight: 1.5 }}>
              Simulate paper trading using historical agent predictions.
            </p>
            <div className="flex gap-3 mb-6">
              <div className="flex-1 bg-black/30 p-2 rounded-lg border border-white/5 flex">
                <input 
                  type="number" 
                  value={sandboxDays} 
                  onChange={(e) => setSandboxDays(Number(e.target.value))}
                  className="bg-transparent text-white w-full outline-none px-2"
                  min="1"
                  title="Simulation Days"
                />
                <span className="text-gray-500 pr-2">d</span>
              </div>
              <div className="flex-1 bg-black/30 p-2 rounded-lg border border-white/5 flex">
                <span className="text-gray-500 pl-2">₹</span>
                <input 
                  type="number" 
                  value={capital} 
                  onChange={(e) => setCapital(Number(e.target.value))}
                  className="bg-transparent text-white w-full outline-none px-2"
                  min="1000"
                  title="Initial Capital"
                />
              </div>
            </div>
            <button 
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-lg text-white font-medium transition-all"
              style={{ background: "rgba(34,197,94,0.8)", boxShadow: "0 4px 14px 0 rgba(34,197,94,0.39)" }}
              onClick={() => openStream(`sandbox/stream?days=${sandboxDays}&capital=${capital}`)}
            >
              <TerminalSquare size={18} />
              Start & Stream Logs
            </button>
          </div>
          
        </div>
      </div>
    </>
  );
}
