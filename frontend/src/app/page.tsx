import { fetchSandboxAgents, fetchLatestPredictions } from "@/lib/api";
import { TrendingUp, Activity, Award, ArrowRight } from "lucide-react";
import Link from "next/link";

export default async function Home() {
  let agents = [];
  let predictions = [];
  let error = null;
  
  try {
    agents = await fetchSandboxAgents();
    predictions = await fetchLatestPredictions();
  } catch (err) {
    error = "Could not connect to the Master Stock API. Ensure it is running on port 8000.";
  }

  const bestAgent = agents.length > 0 ? agents[0] : null;
  const topBuy = predictions.find((p: any) => p.suggested_action === "BUY");

  return (
    <div className="animate-fade-in">
      <h1 className="text-gradient mb-8" style={{ fontSize: '36px' }}>Dashboard Overview</h1>
      
      {error && (
        <div className="glass-card mb-8" style={{ borderLeft: '4px solid var(--danger)' }}>
          <p className="text-danger">{error}</p>
        </div>
      )}

      <div className="stat-grid">
        <div className="glass-card">
          <div className="flex justify-between items-center text-muted">
            <span className="stat-label">Top Agent Return</span>
            <TrendingUp size={20} color="var(--success)" />
          </div>
          <div className="stat-value text-success">
            {bestAgent ? `+${bestAgent.cumulative_return_pct.toFixed(2)}%` : "---"}
          </div>
          <p className="text-muted" style={{ fontSize: '14px' }}>
            {bestAgent ? bestAgent.agent_name : "No data available"}
          </p>
        </div>

        <div className="glass-card">
          <div className="flex justify-between items-center text-muted">
            <span className="stat-label">Active Predictions</span>
            <Activity size={20} color="var(--primary)" />
          </div>
          <div className="stat-value">{predictions.length || "---"}</div>
          <p className="text-muted" style={{ fontSize: '14px' }}>For current trading day</p>
        </div>

        <div className="glass-card">
          <div className="flex justify-between items-center text-muted">
            <span className="stat-label">Top Recommendation</span>
            <Award size={20} color="var(--warning)" />
          </div>
          <div className="stat-value">{topBuy ? topBuy.symbol : "---"}</div>
          <p className="text-muted" style={{ fontSize: '14px' }}>
            {topBuy ? `${(topBuy.confidence * 100).toFixed(0)}% Confidence` : "No strong buys"}
          </p>
        </div>
      </div>

      <div className="flex gap-8 mt-8">
        <div className="glass-card" style={{ flex: 1 }}>
          <div className="flex justify-between items-center mb-6">
            <h2 style={{ fontSize: '20px' }}>Recent Predictions</h2>
            <Link href="/predictions" className="text-primary flex items-center gap-4" style={{ fontSize: '14px' }}>
              View All <ArrowRight size={16} />
            </Link>
          </div>
          
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Confidence</th>
                  <th>Exp. Move</th>
                </tr>
              </thead>
              <tbody>
                {predictions.slice(0, 5).map((pred: any) => (
                  <tr key={pred.symbol}>
                    <td style={{ fontWeight: 600 }}>{pred.symbol}</td>
                    <td>
                      <span className={`badge ${pred.suggested_action.toLowerCase()}`}>
                        {pred.suggested_action}
                      </span>
                    </td>
                    <td>{(pred.confidence * 100).toFixed(1)}%</td>
                    <td className={pred.expected_move_pct >= 0 ? "text-success" : "text-danger"}>
                      {pred.expected_move_pct > 0 ? "+" : ""}{pred.expected_move_pct}%
                    </td>
                  </tr>
                ))}
                {predictions.length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-muted" style={{ textAlign: 'center' }}>No predictions available</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-card" style={{ flex: 1 }}>
          <div className="flex justify-between items-center mb-6">
            <h2 style={{ fontSize: '20px' }}>Agent Performance</h2>
            <Link href="/sandbox" className="text-primary flex items-center gap-4" style={{ fontSize: '14px' }}>
              View All <ArrowRight size={16} />
            </Link>
          </div>
          
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Return</th>
                  <th>Trades</th>
                </tr>
              </thead>
              <tbody>
                {agents.slice(0, 5).map((agent: any) => (
                  <tr key={agent.agent_name}>
                    <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{agent.agent_name}</td>
                    <td className={agent.cumulative_return_pct >= 0 ? "text-success" : "text-danger"}>
                      {agent.cumulative_return_pct > 0 ? "+" : ""}{agent.cumulative_return_pct.toFixed(2)}%
                    </td>
                    <td>{agent.total_trades}</td>
                  </tr>
                ))}
                {agents.length === 0 && (
                  <tr>
                    <td colSpan={3} className="text-muted" style={{ textAlign: 'center' }}>No agents available</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
