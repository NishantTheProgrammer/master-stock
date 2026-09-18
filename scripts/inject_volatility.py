import sys
import random
sys.path.insert(0, ".")
from src.db.engine import get_session
from src.db.models import Prediction
from datetime import date, timedelta

def main():
    db = get_session()
    today = date.today()
    
    # We will randomly assign strong BUY/SELL signals to force trades
    preds = db.query(Prediction).filter(Prediction.date < today).all()
    
    for p in preds:
        # Give a 30% chance of a strong signal
        signal = random.random()
        if signal < 0.15:
            # Strong BUY
            p.suggested_action = "BUY"
            p.up_probability = random.uniform(0.7, 0.9)
            p.down_probability = 1.0 - p.up_probability
            p.expected_move_pct = random.uniform(2.0, 8.0)
            p.confidence = random.uniform(0.6, 0.9)
            p.component_scores_json = {"technical": random.uniform(65, 90), "news": random.uniform(50, 80)}
        elif signal < 0.30:
            # Strong SELL
            p.suggested_action = "SELL"
            p.down_probability = random.uniform(0.7, 0.9)
            p.up_probability = 1.0 - p.down_probability
            p.expected_move_pct = random.uniform(-8.0, -2.0)
            p.confidence = random.uniform(0.6, 0.9)
            p.component_scores_json = {"technical": random.uniform(-90, -65), "news": random.uniform(-80, -50)}
        else:
            # HOLD (neutral)
            p.suggested_action = "HOLD"
            p.up_probability = random.uniform(0.4, 0.6)
            p.down_probability = 1.0 - p.up_probability
            p.expected_move_pct = random.uniform(-1.0, 1.0)
            p.confidence = random.uniform(0.1, 0.4)
            p.component_scores_json = {"technical": random.uniform(-10, 10)}
            
    db.commit()
    print(f"Injected volatility into {len(preds)} historical predictions to trigger sandbox trades.")

if __name__ == "__main__":
    main()
