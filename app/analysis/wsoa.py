import pandas as pd
from .gap import detect_gaps

def wsoa_backtest(coll, hist_cut, years, top_n, th):
    results = coll.get(include=["metadatas"])
    ids = results["ids"]
    metas = results["metadatas"]
    hist_ids = [pid for pid, m in zip(ids, metas) if m.get('filing_date','') <= hist_cut]
    gaps = detect_gaps(coll, th)
    preds = [pid for pid,_ in sorted(gaps.items(), key=lambda x: x[1], reverse=True) if pid in hist_ids][:top_n]
    future_ids = [pid for pid, m in zip(ids, metas)
                  if m.get('filing_date','') > hist_cut and
                  m.get('filing_date','') <= str(pd.to_datetime(hist_cut)+pd.DateOffset(years=years))]
    hits = sum(1 for p in preds if p in future_ids)
    return hits/len(preds) if preds else 0.0
