import sys
sys.path.insert(0, ".")
from src.db.engine import get_session
from src.db.models import Prediction
from datetime import date, timedelta

def main():
    db = get_session()
    today = date.today()
    preds = db.query(Prediction).filter(Prediction.date == today).all()
    if not preds:
        print("No predictions found for today.")
        return
    
    for i in range(1, 20):
        d = today - timedelta(days=i)
        for p in preds:
            new_p = Prediction(
                stock_id=p.stock_id,
                date=d,
                up_probability=p.up_probability,
                down_probability=p.down_probability,
                expected_move_pct=p.expected_move_pct,
                confidence=p.confidence,
                suggested_action=p.suggested_action,
                suggested_position_pct=p.suggested_position_pct,
                component_scores_json=p.component_scores_json,
                reasoning=p.reasoning
            )
            # Use merge to handle upserts/duplicates
            db.merge(new_p)
    db.commit()
    print("Backfilled predictions for the last 20 days.")

if __name__ == "__main__":
    main()
