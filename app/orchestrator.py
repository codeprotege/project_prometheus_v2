import nltk
from tqdm import tqdm
import chromadb
from app.harvesters.mock_harvester import harvest_patents
from app.nlp.keyword_extractor import extract_keywords
from app.nlp.weighting import weight_keywords
from app.embeddings.patent_sberta import embed
from app.storage.chroma_store import init_vector_store
from app.analysis.gap import detect_gaps
from app.analysis.scoring import score_patent
from app.analysis.wsoa import wsoa_backtest

def run_pipeline(cfg, keyword):
    # 1) Harvest
    patents = list(harvest_patents(cfg['sources']['max_patents'], cfg['cpc_focus'], keyword))

    # 2) Keywords
    stop_set = set(nltk.corpus.stopwords.words("english"))
    for rec in tqdm(patents, desc="Keywords"):
        tf = extract_keywords(rec['abstract'], stop_set)
        rec['keywords'] = weight_keywords(rec['abstract'], tf, cfg)

    # 3) Embedding + store
    coll = init_vector_store(cfg)
    docs, ids, metas = [], [], []
    for rec in patents:
        enriched = f"{rec['title']} {rec['abstract']} " + " ".join(rec['keywords'])
        docs.append(enriched)
        ids.append(rec['patent_id'])
        metas.append({'assignee': rec['assignee'], 'cpc': " ".join(rec['cpc']), 'filing_date': rec['filing_date']})

    embs = embed(docs, cfg['embedding_model'])

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
