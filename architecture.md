# Software Architecture – AI-Powered Patent Analytics Platform

## 1. Overview
This document captures the complete software architecture of the end-to-end patent-analytics system that ingests patent data, enriches it with NLP techniques, embeds it into a vector store, and surfaces insights such as blockbuster scores and **White-Space Opportunity Accuracy (WSOA)**.

## 2. Architectural Objectives
* Fully automated data-to-insight pipeline
* Modular, easily extensible codebase
* Reproducible environments via YAML + requirements
* Scalable vector search with sub-second latency
* Traceable ML metrics with reproducible back-testing

## 3. High-Level Component Diagram
```
┌───────────────┐    ┌────────────────┐    ┌────────────────┐
│  User Input   │ → │  main.py CLI   │ → │  Pipeline Core │
└───────────────┘    └────────────────┘    └────────────────┘
                                         ↓
                                 ┌────────────────┐
                                 │ Vector Store   │
                                 │  (ChromaDB)    │
                                 └────────────────┘
                                         ↓
                                 ┌────────────────┐
                                 │ Reports / CSV  │
                                 └────────────────┘
```

## 4. Layered Architecture
| Layer | Purpose | Key Packages |
|-------|---------|--------------|
| **User Interface** | Command-line entry point (`main.py`) & YAML config | `argparse`, `PyYAML` |
| **Application** | Orchestrates stages, handles errors & logging | `logging`, `tqdm` |
| **AI / ML** | Keyword extraction, weighting, embeddings, scoring | `nltk`, `spaCy`, `sentence-transformers`, `scikit-learn` |
| **Data Storage** | Persistent vector DB & metadata cache | `chromadb`, local FS |
| **External APIs** | Patent harvesting & market signals | `patent_client`, `requests` |

## 5. Data-Processing Pipeline
1. **Patent Harvesting** – `harvest_patents()` pulls docs via USPTO or keyword search.
2. **Keyword Extraction & Weighting** – TF-IDF + TextRank + YAKE, five-factor weighting.
3. **Semantic Enrichment** – Inject weighted keywords into abstract/title text.
4. **Embedding Generation** – PatentSBERTa → 768-dim vectors.
5. **Vector Storage** – `ChromaDB` collection (HNSW, cosine).
6. **Analysis Engine** – Similarity matrix, gap detection, blockbuster scoring.
7. **WSOA Back-Test** – Historical snapshot, future-fill validation, accuracy metric.
8. **Reporting** – Console summary + optional CSV export.

## 6. Module & File Map
| File | Responsibility |
|------|----------------|
| `main.py` | Entry script; parses args, loads config, runs pipeline |
| `config.yaml` | Declarative settings (sources, thresholds, model path) |
| `requirements.txt` | Pin exact Python dependencies |
| `startup-guide.md` | Quick-start instructions |
| `code-assets.md` | One-stop bundle for manual inspection |

## 7. Technology Stack
* **Language** – Python 3.11
* **Vector DB** – ChromaDB 0.4.x (HNSW index)
* **Embedding Model** – `AI-Growth-Lab/PatentSBERTa`
* **NLP** – spaCy (en_core_web_sm), NLTK
* **ML / Metrics** – scikit-learn
* **Packaging** – `pip`, virtualenv, Dockerfile (optional for Render.com)

## 8. Data Flow Sequence
```
User → CLI → Patent Harvest  →  Keyword NLP  →  Embeddings  →  Vector Store
                                        ↓                         ↓
                                 Gap Detection               Similarity
                                        ↓                         ↓
                             Scoring & WSOA Metric   ←   Back-Test Validator
                                        ↓
                                CSV / Console Report
```

## 9. Deployment & Environment
* **Local** – `python -m venv`, `pip install -r requirements.txt`.
* **Cloud (Render.com)** – Dockerfile with persistent disk mount for `data/chroma_store`.
* **GPU** – Optional: install `torch` with CUDA before `sentence-transformers`.

## 10. Scalability & Performance
* HNSW index enables O(log N) nearest-neighbor search.
* Pipeline processes ~100 patents/minute on 8-core CPU.
* Embedding batching tunable via `batch_size` config.

## 11. Security & Compliance
* USPTO data is public domain.
* No PII stored; only patent metadata.
* External APIs governed by respective ToS.

## 12. Extensibility Points
* **Additional Data Sources** – Implement new harvesters and register in `config.yaml`.
* **Alternate Models** – Swap `embedding_model` path.
* **Visualization** – Plug in Plotly dashboards reading from vector DB.
* **API Layer** – Expose Flask/FastAPI endpoints for real-time similarity queries.

## 13. Future Enhancements
* Real-time streaming ingest of daily patent grants.
* Cross-lingual embeddings for JP/CN patents.
* Graph neural network for citation analysis.

---
© 2025 Patent Analytics Project – MIT Licensed