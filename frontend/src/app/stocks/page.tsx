import { fetchLatestScores } from "@/lib/api";

export default async function StocksPage() {
  let scores = [];
  let error = null;
  
  try {
    scores = await fetchLatestScores();
  } catch (err) {
    error = "Could not connect to the API to fetch scores.";
  }

  // Function to render score cell with color coding
  const ScoreCell = ({ scoreObj }: { scoreObj: any }) => {
    if (!scoreObj) return <td className="text-muted">---</td>;
    const score = scoreObj.score;
    const colorClass = score > 20 ? "text-success" : score < -20 ? "text-danger" : "text-muted";
    return (
      <td>
        <div className={`flex flex-col ${colorClass}`}>
          <span style={{ fontWeight: 600 }}>{score > 0 ? "+" : ""}{score.toFixed(1)}</span>
          <span style={{ fontSize: '11px', opacity: 0.7 }}>conf: {(scoreObj.confidence * 100).toFixed(0)}%</span>
        </div>
      </td>
    );
  };

  return (
    <div className="animate-fade-in">
      <h1 className="text-gradient mb-8" style={{ fontSize: '36px' }}>Stock Universe & Scores</h1>
      
      {error && (
        <div className="glass-card mb-8" style={{ borderLeft: '4px solid var(--danger)' }}>
          <p className="text-danger">{error}</p>
        </div>
      )}

      <div className="glass-card mb-8">
        <p className="text-muted mb-6">
          Latest AI agent scores for all tracked stocks. Scores range from -100 (Strong Bearish) to +100 (Strong Bullish).
        </p>
        
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Sector</th>
                <th>Technical</th>
                <th>Global News</th>
                <th>Sector News</th>
                <th>Stock News</th>
                <th>Social</th>
              </tr>
            </thead>
            <tbody>
              {scores.map((s: any) => (
                <tr key={s.symbol}>
                  <td style={{ fontWeight: 700, color: 'var(--primary)' }}>{s.symbol}</td>
                  <td className="text-muted">{s.name}</td>
                  <td>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}>
                      {s.sector}
                    </span>
                  </td>
                  <ScoreCell scoreObj={s.technical} />
                  <ScoreCell scoreObj={s.global_news} />
                  <ScoreCell scoreObj={s.sector_news} />
                  <ScoreCell scoreObj={s.stock_news} />
                  <ScoreCell scoreObj={s.social} />
                </tr>
              ))}
              {scores.length === 0 && !error && (
                <tr>
                  <td colSpan={8} className="text-center text-muted p-8">No scores available</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
