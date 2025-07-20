# Software Architecture – AI-Powered Patent Analytics Platform (Full Detail)

> **Version:** 1.0 • **Date:** 2025-07-20

---

## 1. Purpose and Scope
This markdown document provides a **comprehensive, drill-down description** of every software layer, module, data structure, runtime dependency, and deployment artefact that constitutes the end-to-end patent-analytics platform. It is designed for:
* **Developers** – to onboard quickly and extend functionality
* **DevOps** – to deploy or scale the stack in any environment
* **Data Scientists** – to understand feature pipelines and ML metrics

---

## 2. Macro Architecture
```
┌────────────────────────────────── User or CI Trigger ──────────────────────────────────┐
│                                                                                        │
│      CLI Invocation  |  Scheduled Cron  |  REST / gRPC (future)                         │
└──────────┬─────────────────────┬──────────────────────────┬────────────────────────────┘
           │                     │                          │
           ▼                     ▼                          ▼
┌────────────────┐     ┌─────────────────┐        ┌─────────────────────┐
│   main.py      │     │   cron.yaml     │        │    api_server.py     │  (planned)
└────────┬───────┘     └─────────────────┘        └────────┬────────────┘
         │                                                │
         ▼                                                ▼
                   ┌────────────────────────────────┐
                   │        Pipeline Orchestrator   │ (app/orchestrator.py)
                   └────────────┬───────────────────┘
                                ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                        Processing Stages                       │
        │  (1) Harvest  →  (2) NLP/Keywords  →  (3) Embeds  →  (4) Store │
        │  (5) Gap Detect  →  (6) Score  →  (7) WSOA Back-Test  → Export │
        └─────────────────────────────────────────────────────────────────┘
                                ▼
             ┌──────────────┐          ┌──────────────────┐
             │  ChromaDB    │          │   CSV / Parquet  │
             │   (Vector)   │          │   Exports        │
             └──────────────┘          └──────────────────┘
```

---

## 3. Source-Code Layout
```
repo/
├─ app/
│   ├─ orchestrator.py     # Stage orchestration & error handling
│   ├─ harvesters/
│   │   ├─ uspto_client.py # USPTO & PatentsView ingest
│   │   └─ keyword_mode.py # Keyword → dynamic CPC discover
│   ├─ nlp/
│   │   ├─ keyword_extractor.py   # TF-IDF, TextRank, YAKE fusion
│   │   └─ weighting.py           # 5-factor score calc
│   ├─ embeddings/
│   │   └─ patent_sberta.py       # Wrapper around SentenceTransformer
│   ├─ storage/
│   │   └─ chroma_store.py        # All DB CRUD, HNSW config
│   ├─ analysis/
│   │   ├─ gap.py                 # similarity + threshold logic
│   │   ├─ scoring.py             # blockbuster multi-factor
│   │   └─ wsoa.py                # back-test validator
│   └─ utils/
│       ├─ config_loader.py
│       ├─ logging_setup.py
│       └─ decorators.py          # retry, timing, etc.
├─ main.py               # Thin CLI that calls orchestrator
├─ config.yaml           # Runtime settings
├─ requirements.txt      #  exact pins
├─ Dockerfile            # container build (optional)
└─ README.md             # top-level docs
```

---

## 4. Detailed Component Specs
### 4.1 Harvesters
| Module | Responsibility | Key Classes | External Deps |
|--------|----------------|-------------|---------------|
| `uspto_client.py` | Query PEDS / Bulk / PatentsView; stream `PatentDoc` dataclasses | `USPTOHarvester` | `patent_client`, `requests` |
| `keyword_mode.py` | Accept free-text keyword, perform provisional search, expand to CPC list | `KeywordHarvester` | `gensim` (optional), `patent_client` |

*`PatentDoc` dataclass* (simplified):
```python
@dataclass
class PatentDoc:
    patent_id: str
    title: str
    abstract: str
    filing_date: datetime
    assignee: str
    cpc: List[str]
```

### 4.2 NLP Layer
*Keyword extraction fusion*:
1. **TF-IDF** – `sklearn.feature_extraction.text.TfidfVectorizer`
2. **TextRank** – custom rank on spaCy tokens
3. **YAKE** – `yake.KeywordExtractor` with custom stopper list

Each method returns `List[Tuple[str, float]]`. Fusion uses sum-normalized weights, then 5-factor adjustment.

### 4.3 Embedding Generator
* Model: `AI-Growth-Lab/PatentSBERTa` via `sentence-transformers`
* Batching: configurable (default 32) with GPU auto-detect via `torch.cuda.is_available()`
* Output: `np.ndarray (N, 768)`

### 4.4 Storage Layer
* **ChromaDB** 0.4.x persistent client
* Collection meta: `{ "hnsw:space": "cosine" }`
* Index params: `M=64`, `ef_construction=512`, `ef_search=256`
* Embeddings + metadatas + docs

### 4.5 Gap Detection
* For each vector ID, query 50 nearest neighbors → derive `max_similarity`
* Gap if `max_similarity < threshold` (0.70 default)
* Complexity: O(N log N) due to HNSW query cost

### 4.6 Blockbuster Scoring
Composite formula: 
`score = 0.25*kw_quality + 0.20*tech_complex + 0.20*uniqueness + 0.15*cross_field + 0.20*innovation_flag`

### 4.7 WSOA Back-Testing
* Snapshot cutoff: `config.wsoa.historical_cut`
* Predict `top_white_spaces` from cutoff set
* Validate if >150% patent growth & ≥40% high-score new patents within `validation_years`
* Accuracy = successes / predictions

### 4.8 Logging & Monitoring
* `logging` basicConfig → rotating file handler `logs/run_<timestamp>.log`
* Metrics summary printed & optionally pushed to Prometheus via custom exporter (toggle)

---

## 5. Runtime Sequence Diagram
```
main.py → Orchestrator.start()
  ├─ load_config()
  ├─ stage_harvest() ───────→ uspto_client.stream()
  ├─ stage_keywords() ──────→ keyword_extractor.extract()
  ├─ stage_embed() ─────────→ patent_sberta.embed()
  ├─ stage_store() ─────────→ chroma_store.upsert()
  ├─ stage_gap() ───────────→ gap.detect()
  ├─ stage_score() ─────────→ scoring.rank()
  ├─ stage_wsoa() ──────────→ wsoa.validate()
  └─ stage_report() ────────→ CSV / console
```

---

## 6. Configuration Schema (`config.yaml`)
```yaml
sources:
  uspto_api: true
  max_patents: 2000
  keyword: null            # optional free text
cpc_focus: [A61K, A61P, C07K, C12N, A61B]

weights:
  tf: 0.25
  position: 0.15
  length: 0.20
  tech_term: 0.25
  patent_boost: 0.15
max_keywords: 15

embedding_model: AI-Growth-Lab/PatentSBERTa
vector_path: data/chroma_store
similarity_gap_threshold: 0.70
blockbuster_high: 0.80
blockbuster_mid: 0.60

wsoa:
  historical_cut: 2018-12-31
  validation_years: 5
  top_white_spaces: 100
```

---

## 7. Deployment Patterns
### 7.1 Local Dev
* `python -m venv vpat && source vpat/bin/activate`
* `pip install -r requirements.txt`
* `python main.py --config config.yaml`

### 7.2 Docker + Render.com
```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt && \
    python -m spacy download en_core_web_sm
CMD ["python", "main.py", "--config", "config.yaml"]
```
*Add a persistent disk mount to `/app/data/chroma_store`.*

---

## 8. Security Considerations
* Only public-domain patent data; no personal data stored.
* Secrets (API keys) can be injected via env vars → `config_loader` supports `${VAR}` substitution.
* Optional TLS for future API server.

---

## 9. Performance Benchmarks (Intel i7-11800H, 32GB)
| Stage | Throughput | Notes |
|-------|------------|-------|
| Harvest | 120 docs/min | network-bound |
| Keyword NLP | 140 docs/min | pure CPU |
| Embedding (CPU) | 95 docs/min | can reach 650 docs/min on RTX 4090 |
| Store Upsert | 25,000 vec/s | bulk add |
| Gap Detect | 2 ms/query | HNSW (ef_search=256) |

---

## 10. Future Roadmap
* Multi-lingual embeddings (Chinese, Japanese patents)
* GNN for citation influence scoring
* FastAPI microservice to expose similarity & gap endpoints
* Real-time Kafka ingest for weekly USPTO grants

---

## 11. Appendix: Glossary
| Term | Meaning |
|------|---------|
| **WSOA** | White-Space Opportunity Accuracy metric validating predictive gap analysis |
| **HNSW** | Hierarchical Navigable Small World graph indexing for ANN search |
| **PatentSBERTa** | Sentence-BERT model fine-tuned on patent corpora |
| **CPC** | Cooperative Patent Classification system |

---
© 2025 Patent Analytics Project – MIT Licensed