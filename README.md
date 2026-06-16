# PubMed RAG Comparison Pipeline

An end-to-end data engineering and MLOps project that ingests biomedical research papers from PubMed, builds a Retrieval-Augmented Generation (RAG) system for scientific Q&A, and automates embedding and generation model evaluation and promotion — all orchestrated with Apache Airflow on Databricks.

---

## What it does

Ask a natural language question and get an answer grounded in real PubMed research literature:

> **"What factors reduce viscosity in protein formulations?"**
> → Retrieves the most relevant research excerpts → Generates a grounded answer → Cites source papers

---

## Architecture

```
PubMed API
    ↓
Python Ingestion (local, Airflow PythonOperator)
    ↓
Databricks Unity Catalog — bronze.abstracts
    ↓
Spark + LangChain chunking (Databricks Job)
    ↓
Databricks Unity Catalog — silver.chunks
    ↓
Sentence Transformers embedding (Databricks Job)
    ↓
Databricks Unity Catalog — silver.embeddings
    ↓
Databricks Vector Search index
    ↓
Generation model  + Gradio chat UI
```

All jobs are orchestrated by **Apache Airflow** and scheduled weekly.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow |
| Data platform | Databricks (Unity Catalog, Delta Lake, Jobs) |
| Data processing | Apache Spark (PySpark) |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Embedding models | Sentence Transformers (HuggingFace) |
| Vector search | Databricks Vector Search |
| Generation models | HuggingFace Transformers (flan-t5) |
| Experiment tracking | MLflow |
| Evaluation/judging | Gemini (Google API) |
| Interactive UI | Gradio |
| Language | Python |

---

## Key Features

### Medallion Architecture
Data flows through medallion architecture, with gold being reserved for future processing and modelling using dbt models for staging, intermediate joins, and analysis-ready marts.

### Automated Model Evaluation + Promotion + Rollback
The standout feature of this project — two separate evaluation pipelines run on a schedule and automatically promote better-performing models without manual intervention:

**Embedding model evaluation**
- Generates synthetic Q&A pairs from chunks using Claude
- Scores each candidate model on Hit Rate@5 and MRR (Mean Reciprocal Rank)
- If a better model is found, automatically updates the production config and triggers a full re-embedding + vector index rebuild

**Generation model evaluation**
- Uses Claude as an LLM judge to score answers on faithfulness, relevance, and conciseness (1–5 each)
- Computes a composite score and promotes the best performer

### Production Config Table with Rollback
All model promotion events write a new versioned row to a `production_config` Delta table — embedding model, generation model, dimensions, and timestamp. The RAG query layer always reads the latest version. Rolling back to any previous configuration is a single function call.

```
config_version | updated_at       | updated_by           | gen_model     | emb_model      | emb_dim
1               | 2026-06-01 10:00 | initial_setup        | flan-t5-base  | MiniLM-L6      | 384
2               | 2026-06-08 03:00 | embedding_promotion  | flan-t5-base  | specter2_base  | 768
3               | 2026-06-08 04:00 | generation_promotion | flan-t5-large | specter2_base  | 768
```

### Airflow DAGs
Four DAGs coordinate the full system:

- **`ingest_and_chunk`** — weekly ingestion → chunking
- **`embed_and_vector`** —  embedding → vector index sync
- **`embedding_model_promotion`** — embedding model evaluation + automated promotion
- **`generation_model_promotion`** — generation model evaluation + automated promotion

---

## Project Structure

```
rag_pipeline/
├── pipelines/
│   └── pubmed_to_databricks.py      # PubMed ingestion + write to bronze
├── steps/
│   ├── pubmed_to_df.py              # PubMed API client
│   └── df_to_delta_table.py         # Delta Lake writer
├── databricks_notebooks/
│   ├── abstracts_to_chunks.py       # Spark chunking job
│   ├── chunks_to_embeddings.py      # Sentence Transformer embedding job
│   ├── job_create_vector_index.py   # Vector Search index creation/sync
│   ├── generate_eval_set.py         # Synthetic Q&A generation
│   ├── evaluate_embedding_models.py # Embedding model comparison
│   ├── evaluate_generation_models.py# Generation model comparison
│   └── rag_query.py                 # Retrieval + generation query layer
├── databricks_jobs/
│   └── job_*.py                     # Databricks SDK job definitions
├── model_testing_notebooks/
│   └── gradio_app.py                # Interactive Gradio chat UI
├── airflow/
│   └── dags/
│       ├── rag_pipeline.py
│       ├── model_evaluation_dag.py
│       └── generation_model_evaluation_dag.py
└── util/
    ├── get_job_ids.py               # Databricks job ID lookup
    └── production_config.py         # Config table read/write/rollback
```

---

## Data Pipeline (Detailed)

### 1. Ingestion
PubMed's E-utilities API is queried for a configurable search term (e.g. "Viral Vectors"). Article metadata and abstracts are written to `bronze.abstracts` and `bronze.pubmed_meta` as managed Delta tables in Unity Catalog.

### 2. Chunking
A Databricks Spark job reads `bronze.abstracts`, splits abstracts into overlapping text chunks using LangChain's `RecursiveCharacterTextSplitter`, and writes chunk-level records to `silver.chunks`. Uses Pandas UDFs for efficient distributed processing.

### 3. Embedding
A configurable Sentence Transformers model (resolved from `production_config`) encodes each chunk into a dense vector. Models are cached to a Databricks Volume to avoid re-downloading across runs. Outputs written to `silver.embeddings` with Change Data Feed enabled for Vector Search sync.

### 4. Vector Search
A Databricks Vector Search endpoint and delta-sync index are created (or synced) against `silver.embeddings`. The index automatically handles dimension changes when the embedding model is promoted.

### 5. RAG Query
At query time, the question is embedded with the same production model, the vector index returns the top-5 most similar chunks, and a generation model produces an answer grounded in those chunks. The Gradio app provides an interactive chat interface.

---

## Model Evaluation

### Embedding Models Compared
| Model | Dimensions | Hit Rate@5 | MRR |
|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | — | — |
| `all-mpnet-base-v2` | 768 | — | — |
| `allenai/specter2_base` | 768 | — | — |

*Results populated after evaluation runs — `specter2_base` expected to perform best on scientific text.*

### Generation Models Compared
| Model | Avg Faithfulness | Avg Relevance | Avg Conciseness | Composite |
|---|---|---|---|---|
| `flan-t5-base` | — | — | — | — |
| `flan-t5-large` | — | — | — | — |

*All generation scores judged by Gemini (Google) on a 1–5 rubric.*

---

## Domain Relevance

This project was designed around real research domains from my background:

- **Pharmaceutical/biotech** — PubMed queries on drug formulations, protein stability, viral vectors, and bioprocessing (directly relevant to my work at Johnson & Johnson and Bayer)

The RAG system is positioned as a practical tool for literature review automation — a genuine use case in pharma/biotech R&D.

---

## Setup

### Prerequisites
- Python 3.14+
- Databricks workspace (Unity Catalog enabled)
- Apache Airflow 3.x
- Google API key (for evaluation judging, can use free models)

### Environment Variables
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_CATALOG=rag_pipeline
ANTHROPIC_API_KEY=sk-ant-...
```

### Airflow Variables
```bash
airflow variables set embedding_model_name "sentence-transformers/all-MiniLM-L6-v2"
airflow variables set embedding_model_path "/Volumes/rag_pipeline/silver/models/all-MiniLM-L6-v2"
airflow variables set embedding_dimension "384"
airflow variables set embedding_model_hit_rate "0"
airflow variables set generation_model_name "google/flan-t5-base"
airflow variables set generation_model_score "0"
```

### Run
```bash
# Start Airflow
export AIRFLOW_HOME=~/rag_pipeline/airflow
airflow standalone

# Trigger the pipeline manually
airflow dags trigger rag_pipeline
```

---

## Skills Demonstrated

- **Data engineering** — end-to-end pipeline design, medallion architecture, Delta Lake, Unity Catalog
- **Distributed computing** — PySpark, Pandas UDFs, Arrow-based batch processing
- **MLOps** — MLflow experiment tracking, automated model evaluation, versioned config promotion, rollback
- **Orchestration** — Airflow DAGs, task dependencies, branching, cross-DAG triggers
- **NLP/ML** — embedding models, vector search, RAG architecture, LLM-as-judge evaluation
- **Cloud** — Databricks jobs, serverless compute, Volumes, Vector Search endpoints
- **Software engineering** — modular Python, argparse CLI, configurable pipelines, version-controlled jobs-as-code
