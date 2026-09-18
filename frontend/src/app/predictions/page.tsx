import { fetchLatestPredictions } from "@/lib/api";

export default async function PredictionsPage() {
  let predictions = [];
  let error = null;
  
  try {
    predictions = await fetchLatestPredictions();
  } catch (err) {
    error = "Could not connect to the API to fetch predictions.";
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-gradient mb-8" style={{ fontSize: '36px' }}>AI Predictions</h1>
      
      {error && (
        <div className="glass-card mb-8" style={{ borderLeft: '4px solid var(--danger)' }}>
          <p className="text-danger">{error}</p>
        </div>
      )}

      <div className="grid gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))' }}>
        {predictions.map((pred: any) => {
          const isBuy = pred.suggested_action === 'BUY';
          const isSell = pred.suggested_action === 'SELL';
          
          return (
            <div key={pred.symbol} className="glass-card flex-col gap-4" style={{ position: 'relative', overflow: 'hidden' }}>
              {/* Subtle background glow based on action */}
              <div style={{
                position: 'absolute', top: '-50px', right: '-50px', width: '150px', height: '150px',
                background: isBuy ? 'var(--success)' : isSell ? 'var(--danger)' : 'var(--warning)',
                opacity: 0.1, filter: 'blur(40px)', borderRadius: '50%'
              }} />
              
              <div className="flex justify-between items-center z-10">
                <div>
                  <h2 style={{ fontSize: '24px', margin: 0, color: 'var(--primary)' }}>{pred.symbol}</h2>
                  <span className="text-muted" style={{ fontSize: '14px' }}>{pred.name}</span>
                </div>
                <span className={`badge ${pred.suggested_action.toLowerCase()}`} style={{ fontSize: '14px', padding: '8px 16px' }}>
                  {pred.suggested_action}
                </span>
              </div>
              
              <div className="mt-6 z-10">
                <div className="flex justify-between mb-2">
                  <span className="text-muted">Win Probability</span>
                  <span style={{ fontWeight: 600 }}>{(pred.up_probability * 100).toFixed(1)}%</span>
                </div>
                <div className="progress-bg">
                  <div 
                    className={`progress-fill ${pred.up_probability >= 0.5 ? 'positive' : 'negative'}`} 
                    style={{ width: `${pred.up_probability * 100}%` }}
                  />
                </div>
              </div>
              
              <div className="flex justify-between mt-6 z-10" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                <div className="flex-col">
                  <span className="text-muted" style={{ fontSize: '12px', textTransform: 'uppercase' }}>Exp. Move</span>
                  <span className={pred.expected_move_pct >= 0 ? "text-success" : "text-danger"} style={{ fontSize: '18px', fontWeight: 600 }}>
                    {pred.expected_move_pct > 0 ? "+" : ""}{pred.expected_move_pct.toFixed(2)}%
                  </span>
                </div>
                
                <div className="flex-col" style={{ alignItems: 'flex-end' }}>
                  <span className="text-muted" style={{ fontSize: '12px', textTransform: 'uppercase' }}>Confidence</span>
                  <span style={{ fontSize: '18px', fontWeight: 600 }}>
                    {(pred.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              
              <div className="mt-4 z-10" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                <span className="text-muted mb-2 block" style={{ fontSize: '12px', textTransform: 'uppercase' }}>Score Breakdown</span>
                <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(2, 1fr)', fontSize: '12px' }}>
                  {Object.entries(pred.component_scores_json || {}).map(([key, value]: [string, any]) => (
                    <div key={key} className="flex justify-between items-center bg-black/20 p-2 rounded">
                      <span className="text-muted capitalize" style={{ fontSize: '10px' }}>{key.replace('_', ' ')}</span>
                      <span className={value > 0 ? "text-success" : value < 0 ? "text-danger" : "text-muted"} style={{ fontWeight: 600 }}>
                        {value > 0 ? "+" : ""}{Number(value).toFixed(0)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="mt-4 p-4 z-10" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', fontSize: '14px' }}>
                <span className="text-muted">AI Reasoning:</span> {pred.reasoning}
              </div>
            </div>
          );
        })}
      </div>
      
      {predictions.length === 0 && !error && (
        <div className="glass-card text-center p-8 text-muted">
          No predictions available for the current date.
        </div>
      )}
    </div>
  );
}
