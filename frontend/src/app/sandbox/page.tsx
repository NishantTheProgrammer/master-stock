import { fetchSandboxAgents, fetchSandboxTrades } from "@/lib/api";

export default async function SandboxPage() {
  let agents = [];
  let trades = [];
  let error = null;
  
  try {
    agents = await fetchSandboxAgents();
    trades = await fetchSandboxTrades();
  } catch (err) {
    error = "Could not connect to the API to fetch sandbox data.";
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-gradient mb-8" style={{ fontSize: '36px' }}>Paper Trading Sandbox</h1>
      
      {error && (
        <div className="glass-card mb-8" style={{ borderLeft: '4px solid var(--danger)' }}>
          <p className="text-danger">{error}</p>
        </div>
      )}

      <div className="glass-card mb-8">
        <h2 className="mb-6" style={{ fontSize: '24px' }}>Agent Leaderboard</h2>
        <p className="text-muted mb-6">
          Comparison of different AI trading strategies over historical data. All agents start with ₹1,000,000 capital.
        </p>
        
        <div className="grid gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          {agents.map((agent: any, i: number) => {
            const isWinner = i === 0;
            return (
              <div key={agent.agent_name} className="glass-card" style={{ 
                border: isWinner ? '1px solid rgba(59, 130, 246, 0.5)' : undefined,
                boxShadow: isWinner ? '0 0 20px rgba(59, 130, 246, 0.15)' : undefined
              }}>
                <div className="flex justify-between items-center mb-4">
                  <h3 style={{ textTransform: 'capitalize', fontSize: '20px', margin: 0 }}>
                    {isWinner && "🏆 "} {agent.agent_name}
                  </h3>
                  <span className={agent.cumulative_return_pct >= 0 ? "text-success" : "text-danger"} style={{ fontWeight: 700, fontSize: '18px' }}>
                    {agent.cumulative_return_pct > 0 ? "+" : ""}{agent.cumulative_return_pct.toFixed(2)}%
                  </span>
                </div>
                
                <div className="flex-col gap-2 mt-4 text-muted" style={{ fontSize: '14px' }}>
                  <div className="flex justify-between">
                    <span>Portfolio Value:</span>
                    <span style={{ color: 'var(--text-main)' }}>₹{agent.portfolio_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Drawdown:</span>
                    <span style={{ color: 'var(--text-main)' }}>{agent.max_drawdown_pct.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Trades:</span>
                    <span style={{ color: 'var(--text-main)' }}>{agent.total_trades}</span>
                  </div>
                </div>
              </div>
            );
          })}
          {agents.length === 0 && !error && (
            <div className="text-muted p-4">No agent performance data found. Run the sandbox simulation first.</div>
          )}
        </div>
      </div>
      
      <div className="glass-card">
        <h2 className="mb-6" style={{ fontSize: '24px' }}>Recent Sandbox Trades</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Agent</th>
                <th>Action</th>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total Value</th>
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, 50).map((trade: any, i: number) => (
                <tr key={i}>
                  <td className="text-muted">{trade.date}</td>
                  <td style={{ textTransform: 'capitalize' }}>{trade.agent_name}</td>
                  <td>
                    <span className={`badge ${trade.action.toLowerCase()}`}>
                      {trade.action}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{trade.symbol}</td>
                  <td>{trade.quantity}</td>
                  <td>₹{trade.price.toFixed(2)}</td>
                  <td>₹{trade.total_cost.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                </tr>
              ))}
              {trades.length === 0 && !error && (
                <tr>
                  <td colSpan={7} className="text-center text-muted p-8">No trades recorded</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
