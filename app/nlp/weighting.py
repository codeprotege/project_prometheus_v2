import re

TECH_REGEX = re.compile(r"[a-z]{3,}\d+")

def weight_keywords(text:str, tf, cfg):
    total = sum(tf.values()) or 1
    scores = {}
    for tok, freq in tf.items():
        tf_w = freq / total
        pos_w = 1 - (text.lower().find(tok) / (len(text)+1))
        len_w = len(tok) / 20
        tech_w = 1 if TECH_REGEX.match(tok) else 0
        score = (cfg['weights']['tf']*tf_w + cfg['weights']['position']*pos_w +
                 cfg['weights']['length']*len_w + cfg['weights']['tech_term']*tech_w)
        if tok in {"claim","apparatus","composition"}:
            score += cfg['weights']['patent_boost']
        scores[tok] = score
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:cfg['max_keywords']])
