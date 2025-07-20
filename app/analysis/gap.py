from tqdm import tqdm

def similarity_to_gap(distances):
    # Chroma returns distances (0=identical for cosine), convert to similarity
    return 1 - min(distances)

def detect_gaps(coll, th):
    ids = coll.get()["ids"]
    embeddings = coll.get(include=["embeddings"])["embeddings"]
    gaps = {}
    for i, pid in enumerate(tqdm(ids, desc="Gap scan")):
        res = coll.query(query_embeddings=[embeddings[i]], n_results=50, include=["distances"])
        sim = similarity_to_gap(res["distances"][0])
        if sim < th:
            gaps[pid] = 1 - sim
    return gaps
