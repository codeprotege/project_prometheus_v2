def score_patent(rec, gap_score, cfg):
    kw_quality = sum(rec['keywords'].values()) / len(rec['keywords'])
    tech_complex = len(rec['abstract']) / 1500
    uniqueness = gap_score
    cross_field = 1 if len(set(rec['cpc'])) > 3 else 0
    innovation = 1 if "novel" in rec['abstract'].lower() else 0
    score = (0.25*kw_quality + 0.20*tech_complex + 0.20*uniqueness +
             0.15*cross_field + 0.20*innovation)
    if score > cfg['blockbuster_high']:
        label = "HIGH"
    elif score > cfg['blockbuster_mid']:
        label = "MEDIUM"
    else:
        label = "LOW"
    return score, label
