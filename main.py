#!/usr/bin/env python3
"""End-to-end patent analytics pipeline with WSOA metric.
Run examples:
  python main.py --config config.yaml                # CPC-based (defaults)
  python main.py --config config.yaml --keyword "ai cancer detection" --max_patents 300
"""
import argparse, os, sys, re, math, datetime as dt, yaml, json
from collections import Counter
import pandas as pd
from tqdm import tqdm
import nltk, spacy
from sentence_transformers import SentenceTransformer
import chromadb
from patent_client import Patent

# ----------------------------- helpers ---------------------------------

def load_cfg(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def harvest_patents(max_docs, cpc_codes=None, keyword=None):
    """Yield dicts with patent metadata & abstract text."""
    if keyword:
        q = Patent.objects.filter(search_text=keyword)[:max_docs]
    else:
        q = Patent.objects.filter(cpc__in=cpc_codes)[:max_docs]
    for p in tqdm(q, desc="Harvesting", unit="patent"):
        yield {
            "patent_id": p.patent_number,
            "title": p.title or "",
            "abstract": p.abstract or "",
            "filing_date": str(p.filing_date) if p.filing_date else "",
            "assignee": p.assignee_name or "",
            "cpc": list(p.cpc)
        }

# ------------------ keyword extraction & weighting ---------------------

spacy_nlp = spacy.load("en_core_web_sm")
stop_set = set(nltk.corpus.stopwords.words("english"))
TECH_REGEX = re.compile(r"[a-z]{3,}\d+")

def weight_keywords(text:str, cfg):
    tokens = nltk.word_tokenize(text.lower())
    tf = Counter(tok for tok in tokens if tok.isalpha() and tok not in stop_set)
    total = sum(tf.values()) or 1
    scores = {}
    for tok, freq in tf.items():
        tf_w = freq / total
        pos_w = 1 - (text.lower().find(tok) / (len(text)+1))
        len_w = len(tok) / 20
        tech_w = 1 if TECH_REGEX.match(tok) else 0
        score = (cfg['tf']*tf_w + cfg['position']*pos_w +
                 cfg['length']*len_w + cfg['tech_term']*tech_w)
        if tok in {"claim","apparatus","composition"}:
            score += cfg['patent_boost']
        scores[tok] = score
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:cfg['max_keywords']])

# -------------------- embedding & vector storage -----------------------

def init_vector_store(cfg):
    client = chromadb.PersistentClient(path=cfg['vector_path'])
    return client.get_or_create_collection(
        name=cfg['collection_name'],
        metadata={"hnsw:space": cfg['similarity_metric']}
    )

model_cache = {}

def get_model(name):
    if name not in model_cache:
        model_cache[name] = SentenceTransformer(name, device="cpu")
    return model_cache[name]

# -------------------------- analysis engine ----------------------------

def similarity_to_gap(distances):
    # Chroma returns distances (0=identical for cosine), convert to similarity
    return 1 - min(distances)

def detect_gaps(coll, th):
    ids = coll.get()["ids"]
    gaps = {}
    for pid in tqdm(ids, desc="Gap scan"):
        res = coll.query(ids=[pid], n_results=50, include=["distances"])
        sim = similarity_to_gap(res["distances"][0])
        if sim < th:
            gaps[pid] = 1 - sim
    return gaps

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

# ------------------- white-space opportunity accuracy ------------------

def wsoa_backtest(coll, hist_cut, years, top_n, th):
    ids, metas = coll.get(include=["metadatas"]).values()
    hist_ids = [pid for pid, m in zip(ids, metas) if m.get('filing_date','') <= hist_cut]
    gaps = detect_gaps(coll, th)
    preds = [pid for pid,_ in sorted(gaps.items(), key=lambda x: x[1], reverse=True) if pid in hist_ids][:top_n]
    future_ids = [pid for pid, m in zip(ids, metas)
                  if m.get('filing_date','') > hist_cut and
                  m.get('filing_date','') <= str(pd.to_datetime(hist_cut)+pd.DateOffset(years=years))]
    hits = sum(1 for p in preds if p in future_ids)
    return hits/len(preds) if preds else 0.0

# ------------------------------- main ----------------------------------

def main():
    parser = argparse.ArgumentParser(description="Patent analytics with WSOA")
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--keyword', help='Run keyword mode instead of CPC list')
    parser.add_argument('--max_patents', type=int, help='Override max patents')
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    if args.max_patents: cfg['sources']['max_patents'] = args.max_patents

    # 1) Harvest
    patents = list(harvest_patents(cfg['sources']['max_patents'], cfg['cpc_focus'], args.keyword))

    # 2) Keywords
    for rec in tqdm(patents, desc="Keywords"):
        rec['keywords'] = weight_keywords(rec['abstract'], cfg['weights'])

    # 3) Embedding + store
    coll = init_vector_store(cfg)
    model = get_model(cfg['embedding_model'])
    docs, ids, metas = [], [], []
    for rec in patents:
        enriched = f"{rec['title']} {rec['abstract']} " + " ".join(rec['keywords'])
        docs.append(enriched)
        ids.append(rec['patent_id'])
        metas.append({'assignee': rec['assignee'], 'cpc': rec['cpc'], 'filing_date': rec['filing_date']})
    embs = model.encode(docs, convert_to_numpy=True, show_progress_bar=True)
    try:
        coll.add(ids=ids, embeddings=embs.tolist(), documents=docs, metadatas=metas)
    except chromadb.errors.IDAlreadyExistsError:
        pass  # incremental run

    # 4) Gap detect
    gap_scores = detect_gaps(coll, cfg['similarity_gap_threshold'])

    # 5) Score patents
    ranked = []
    for rec in patents:
        gap = gap_scores.get(rec['patent_id'], 0)
        score, label = score_patent(rec, gap, cfg)
        ranked.append((rec['patent_id'], score, label))
    ranked.sort(key=lambda x: x[1], reverse=True)

    # 6) WSOA
    wsoa = wsoa_backtest(coll, cfg['wsoa']['historical_cut'], cfg['wsoa']['validation_years'], cfg['wsoa']['top_white_spaces'], cfg['similarity_gap_threshold'])

    # 7) Summary
    high = sum(1 for _,_,l in ranked if l=='HIGH')
    gaps = len(gap_scores)
    print("\nSummary\n-------")
    print(f"Patents ingested ..........: {len(patents)}")
    print(f"Vectors in store ..........: {len(coll.get()['ids'])}")
    print(f"Detected gaps .............: {gaps}")
    print(f"Blockbuster (HIGH) patents : {high}")
    print(f"WSOA back-test accuracy ...: {wsoa:.2f}\n")

if __name__ == "__main__":
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    main()