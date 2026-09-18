const API_BASE = 'http://localhost:8000/api';

export async function fetchStocks() {
  const res = await fetch(`${API_BASE}/stocks`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch stocks');
  return res.json();
}

export async function fetchStockDetails(symbol: string) {
  const res = await fetch(`${API_BASE}/stocks/${symbol}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch stock details');
  return res.json();
}

export async function fetchLatestScores() {
  const res = await fetch(`${API_BASE}/scores/latest`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch latest scores');
  return res.json();
}

export async function fetchLatestPredictions() {
  const res = await fetch(`${API_BASE}/predictions/latest`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch latest predictions');
  return res.json();
}

export async function fetchSandboxResults() {
  const res = await fetch(`${API_BASE}/sandbox/results`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch sandbox results');
  return res.json();
}

export async function fetchSandboxAgents() {
  const res = await fetch(`${API_BASE}/sandbox/agents`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch sandbox agents');
  return res.json();
}

export async function fetchSandboxTrades(agentName?: string) {
  const url = agentName ? `${API_BASE}/sandbox/trades?agent_name=${encodeURIComponent(agentName)}` : `${API_BASE}/sandbox/trades`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch sandbox trades');
  return res.json();
}
