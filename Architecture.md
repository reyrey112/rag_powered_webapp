# ARCHITECTURE.md

## ARCHITECTURE.md

> Reference document for the PubMed RAG Pipeline project.
> Last updated: June 2026 (reconciled with repository layout)

---

## Table of Contents

1. High-Level Overview
2. Repository Structure
3. Data Flow
4. Key Modules & Entry Points
5. Databricks Jobs (jobs-as-code)
6. Airflow DAGs
7. Data Model
8. Configuration & Secrets
9. Naming Conventions
10. Where to Find Things
11. Known Issues

---

## High-Level Overview

This project is an end-to-end RAG (Retrieval-Augmented Generation) pipeline that:

1. Ingests PubMed biomedical research abstracts via the E-utilities API
2. Chunks, embeds, and indexes them in Databricks Vector Search
3. Answers natural language questions grounded in the retrieved literature
4. Automatically evaluates and promotes the best embedding and generation models

Medallion architecture (bronze → silver → gold) on Databricks Delta Lake, orchestrated by Apache Airflow, with MLflow tracking all evaluation experiments:

PubMed API → local ingestion → bronze Delta tables → Databricks chunking job → silver.chunks → embedding job → silver.embeddings → Vector Search index → RAG query layer → Gradio UI

---

## Repository Structure

rag_pipeline/ (top-level)

- pipelines/
    - __init__.py
    - pubmed_to_databricks.py — ingestion entry (run_pipeline)
- steps/
    - __init__.py
    - pubmed_to_df.py
    - df_to_delta_table.py
    - volume_to_delta_table.py
    - csv_to_databricks_volume.py
    - mysql_to_csv.py
- databricks_notebooks/
    - abstracts_to_chunks.py
    - chunks_to_embeddings.py
    - embeddings_to_vector.py
    - vector_index_test.py
    - rag_query.py
    - gradio.py
- databricks_jobs/
    - job_abstract_to_chunks.py
    - job_chunks_to_embeddings.py
    - job_embeddings_to_vector.py
    - job_generate_evaluation_set.py
    - job_evaluate_embedding_models.py
    - job_evaluate_generation_models.py
- model_testing_notebooks/
    - generate_evaluation_set.py
    - evaluate_embedding_models.py
    - evaluate_generation_models.py
- airflow/
    - dags/
        - dag_ingest_and_chunk.py
        - dag_embed_and_vector.py
        - dag_embedding_model_promotion.py
        - dag_generation_model_promotion.py
        - util/
            - get_job_ids.py
            - production_configurations.py
- setup.sh
- .env (gitignored)
- requirements.txt
- README.md
- ARCHITECTURE.md (this file)

---

## Data Flow

1. Ingestion (local → bronze)
     - `steps/pubmed_to_df.PubSearch` : search, fetch, parse PMIDs → list/dicts
     - `steps/df_to_delta_table.write_to_delta_table` writes metadata and abstracts into bronze tables

2. Chunking (bronze → silver)
     - `databricks_notebooks/abstracts_to_chunks.create_chunks` reads bronze abstracts via Spark, splits text, produces `rag_pipeline.silver.chunks`

     - Note: actual splitter parameters in code use `chunk_size=250` and `chunk_overlap=100` (not 1000).

3. Embedding (silver.chunks → silver.embeddings)
     - `databricks_notebooks/chunks_to_embeddings.create_embeddings` encodes chunks using SentenceTransformer
     - Requires CLI args `--model_name` and `--model_path` when invoked (job or DatabricksRunNow passes these)

4. Vector Search (silver.embeddings → index)
     - `databricks_notebooks/embeddings_to_vector.py` ensures endpoint and index exist and triggers delta sync
     - CLI arg: `--embedding_dim` required for job invocation

5. RAG Query (index → answer)
     - `databricks_notebooks/rag_query.rag_query(query)` reads production_config, computes query embedding, calls Vector Search, and generates answers via a generator pipeline

6. Evaluation & Promotion
     - Eval set generation, embedding eval, generation eval implemented in `model_testing_notebooks/` and logged to Delta + MLflow
     - Promotion DAGs update Airflow Variables and call `airflow/dags/util/production_configurations.py` to write a new `production_config` row

---

## Key Modules & Entry Points

- Ingestion pipeline entry: `pipelines/pubmed_to_databricks.run_pipeline()` — script accepts CLI args and calls `write_to_delta_table` (be aware of a syntax issue in default f-strings; see Known Issues).
- PubMed client: `steps/pubmed_to_df.PubSearch` — methods `search`, `fetch`, `list_to_df`.
- Delta writer (local): `steps/df_to_delta_table.write_to_delta_table`.
- Chunking job (Databricks Spark): `databricks_notebooks/abstracts_to_chunks.create_chunks(abstract_table, chunks_table)`.
- Embedding job (Databricks Spark): `databricks_notebooks/chunks_to_embeddings.create_embeddings(chunks_table, embeddings_table, model_name, model_path)` and accepts `--model_name`/`--model_path`.
- Vector index sync: `databricks_notebooks/embeddings_to_vector.py` (entry `main()` — `--embedding_dim` argument).
- RAG query: `databricks_notebooks/rag_query.rag_query(query)` (module-level lazy model loading).
- Evaluation scripts (notebooks/jobs): `model_testing_notebooks/generate_evaluation_set.py`, `model_testing_notebooks/evaluate_embedding_models.py`, `model_testing_notebooks/evaluate_generation_models.py`.

---

## Databricks Jobs (names used in job-definitions)

- `abstract_chunking_pipeline` — runs `databricks_notebooks/abstracts_to_chunks.py`
- `chunks_to_embeddings_pipeline` — runs `databricks_notebooks/chunks_to_embeddings.py` (parameters overridden at runtime)
- `vector_embedding_pipeline` — runs `databricks_notebooks/embeddings_to_vector.py`
- `generate_evaluation_set_pipeline` — runs `model_testing_notebooks/generate_evaluation_set.py`
- `evaluate_embedding_models_pipeline` — runs `model_testing_notebooks/evaluate_embedding_models.py`
- `evaluate_generation_models_pipeline` — runs `model_testing_notebooks/evaluate_generation_models.py`

Important: job names must match exactly when looked up via the Databricks SDK (`get_job_id`).

---

## Airflow DAGs

- `dag_ingest_and_chunk.py` — ingestion `run_pipeline` → Databricks chunking job (`abstract_chunking_pipeline`)
- `dag_embed_and_vector.py` — embedding job (`chunks_to_embeddings_pipeline`) → vector index job (`vector_embedding_pipeline`); resolves `--model_name`, `--model_path`, `--embedding_dim` from Airflow Variables
- `dag_embedding_model_promotion.py` — runs embedding evaluation, decides promotion, updates Variables and `production_config`, optionally triggers `embed_and_vector`
- `dag_generation_model_promotion.py` — runs generation evaluation, decides promotion, updates Variables + `production_config`

Airflow utility functions (job lookup and production config helpers) live under `airflow/dags/util/`.

---

## Data Model (Unity Catalog: rag_pipeline)

- bronze.pubmed_meta — pmid, title, authors, journal, year, mesh_terms, doi  
- bronze.abstracts — pmid, abstract  
- silver.chunks — pmid, chunk_id, chunk_index, chunk  
- silver.embeddings — pmid, chunk_id, chunk_index, chunk, embedding  
- silver.eval_questions / silver.test_questions — question, chunk_id, pmid, source_chunk  
- silver.embedding_eval_results — model, model_path, embedding_dim, hit_rate@5, mrr, evaluated_at  
- silver.generation_eval_results — model, avg_faithfulness, avg_relevance, avg_conciseness, composite_score, evaluated_at  
- silver.production_config — config_version, updated_at, updated_by, generation_model_name, embedding_model_name, embedding_model_path, embedding_dimension

Always read current config via `airflow/dags/util/production_configurations.get_latest_config()`.

---

## Configuration & Secrets

Environment variables (local `.env`, gitignored):
- DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH, DATABRICKS_CATALOG, DATABRICKS_WAREHOUSE_ID, etc.

Databricks secret scope:
- scope: rag_pipeline — contains keys like `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` referenced by evaluation notebooks.

Airflow Variables (used at DAG parse/runtime):
- `embedding_model_name`
- `embedding_model_path`
- `embedding_dimension`
- `embedding_model_hit_rate`
- `generation_model_name`
- `generation_model_score`

---

## Naming Conventions

- Python files/functions: snake_case  
- Classes: PascalCase  
- Databricks job names: `{description}_pipeline` (e.g. `chunks_to_embeddings_pipeline`)  
- Vector Search endpoint: `rag_pipeline_endpoint` (env override allowed)  
- Vector Search index: `rag_pipeline.silver.chunk_index` (default)

Chunk ID format: `{pmid}_chunk_{chunk_index}`

---

## Where to Find Things (file locations)

- PubMed API client: [steps/pubmed_to_df.py](steps/pubmed_to_df.py)  
- Delta table writer (local): [steps/df_to_delta_table.py](steps/df_to_delta_table.py)  
- Full ingestion pipeline: [pipelines/pubmed_to_databricks.py](pipelines/pubmed_to_databricks.py) → `run_pipeline()`  
- Chunking job: [databricks_notebooks/abstracts_to_chunks.py](databricks_notebooks/abstracts_to_chunks.py) → `create_chunks()`  
- Embedding job: [databricks_notebooks/chunks_to_embeddings.py](databricks_notebooks/chunks_to_embeddings.py) → `create_embeddings()`  
- Vector index sync / endpoint: [databricks_notebooks/embeddings_to_vector.py](databricks_notebooks/embeddings_to_vector.py)  
- RAG query layer: [databricks_notebooks/rag_query.py](databricks_notebooks/rag_query.py) → `rag_query()`  
- Gradio UI: [databricks_notebooks/gradio.py](databricks_notebooks/gradio.py)  
- Eval scripts (generation / embedding): [model_testing_notebooks/generate_evaluation_set.py](model_testing_notebooks/generate_evaluation_set.py), [model_testing_notebooks/evaluate_embedding_models.py](model_testing_notebooks/evaluate_embedding_models.py), [model_testing_notebooks/evaluate_generation_models.py](model_testing_notebooks/evaluate_generation_models.py)  
- Databricks job definitions (SDK): [databricks_jobs/](databricks_jobs/) (files beginning with `job_`)  
- Airflow DAGs: [airflow/dags/dag_ingest_and_chunk.py](airflow/dags/dag_ingest_and_chunk.py), [airflow/dags/dag_embed_and_vector.py](airflow/dags/dag_embed_and_vector.py), [airflow/dags/dag_embedding_model_promotion.py](airflow/dags/dag_embedding_model_promotion.py), [airflow/dags/dag_generation_model_promotion.py](airflow/dags/dag_generation_model_promotion.py)  
- Airflow helper utilities: [airflow/dags/util/get_job_ids.py](airflow/dags/util/get_job_ids.py), [airflow/dags/util/production_configurations.py](airflow/dags/util/production_configurations.py)

---

## Known Issues (repo-verified)

- `pipelines/pubmed_to_databricks.py` contains invalid nested double-quotes in default f-strings for `meta_table` and `abstract_table`. This will raise a SyntaxError if the module is imported. Fix: use single quotes inside the f-string or construct defaults at runtime. See [pipelines/pubmed_to_databricks.py](pipelines/pubmed_to_databricks.py).
- ARCH (previous doc) referenced several files under different paths/names — those are corrected above.
- Chunking parameters in code: `chunk_size=250` (not 1000 as older doc stated).

---

If you want, I can prepare a small PR that also fixes the `pipelines/pubmed_to_databricks.py` syntax error.

### Environment variables (`.env`, gitignored)

```
DATABRICKS_HOST         https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN        dapi...
DATABRICKS_HTTP_PATH    /sql/1.0/warehouses/your-id
DATABRICKS_CATALOG      rag_pipeline
GEMINI_API_KEY       sk-ant-...
```

### Databricks Secrets

```
scope: rag_pipeline
  key: GEMINI_API_KEY     used by evaluate_generation_models.py
```

Access in notebooks/jobs:
```python
dbutils.secrets.get(scope="rag_pipeline", key="GEMINI_API_KEY")
```

### Airflow Variables

```
embedding_model_name        current production embedding model HF name
embedding_model_path        Volume path where model weights are saved
embedding_dimension         int, must match vector index
embedding_model_hit_rate    float, used for promotion comparison baseline
generation_model_name       current production generation model HF name
generation_model_score      float, composite score baseline
```

**Airflow Variables are the runtime config for DAGs.**
**`production_config` Delta table is the audit log and serving config for the RAG query layer.**
Both are updated together on every promotion.

---

## Naming Conventions

### Python
- Files: `snake_case.py`
- Functions: `snake_case`
- Classes: `PascalCase` (e.g. `PubSearch`)
- Constants: `ALL_CAPS` (e.g. `MODEL_NAME`, `EVAL_TABLE`)

### Databricks
- Catalog: `rag_pipeline`
- Schema names: `bronze`, `silver`, `gold` (medallion)
- Table names: `snake_case` (e.g. `pubmed_meta`, `chunk_embeddings`)
- Volume paths: `/Volumes/rag_pipeline/silver/models/{model_short_name}/`
- Job names: `{description}_pipeline` (e.g. `abstract_chunking_pipeline`)
- Vector Search endpoint: `rag_pipeline_endpoint`
- Vector Search index: `rag_pipeline.silver.chunk_index`

### Airflow
- DAG IDs: `snake_case` (e.g. `rag_pipeline`, `embedding_model_evaluation_and_promotion`)
- Task IDs: `snake_case` verb-first (e.g. `ingest_pubmed`, `promote_best_model`)
- Variable keys: `snake_case` (e.g. `embedding_model_name`)
- Connection ID: `databricks_default`

### Chunk IDs
Format: `{paper_id}_chunk_{chunk_index}`
Example: `12345678_chunk_3`
Used as primary key in `silver.chunks`, `silver.embeddings`, and the Vector Search index.

---

## Where to Find Things

| What | Where |
|---|---|
| PubMed API logic | `steps/pubmed_to_df.py` → `PubSearch` class |
| Delta table writes (local) | `steps/df_to_delta_table.py` |
| Full ingestion pipeline | `pipelines/pubmed_to_databricks.py` → `run_pipeline()` |
| Chunking logic | `databricks_notebooks/abstracts_to_chunks.py` → `create_chunks()` |
| Embedding logic | `databricks_notebooks/chunks_to_embeddings.py` → `create_embeddings()` |
| Vector index logic | `databricks_notebooks/job_create_vector_index.py` → `ensure_index()` |
| RAG query logic | `databricks_notebooks/rag_query.py` → `rag_query()` |
| Gradio UI | `model_testing_notebooks/gradio_app.py` |
| Synthetic eval set generation | `databricks_notebooks/generate_eval_set.py` |
| Embedding model evaluation | `databricks_notebooks/evaluate_embedding_models.py` |
| Generation model evaluation | `databricks_notebooks/evaluate_generation_models.py` |
| Production config read/write | `util/production_configurations.py` |
| Databricks job ID lookup | `util/get_job_ids.py` |
| Main pipeline DAG | `airflow/dags/rag_pipeline.py` |
| Embedding promotion DAG | `airflow/dags/dag_embedding_model_promotion.py` |
| Generation promotion DAG | `airflow/dags/dag_generation_model_promotion.py` |
| Job definitions (SDK) | `databricks_jobs/job_*.py` |
| Environment setup | `setup.sh` |
| All secrets | Databricks secret scope `rag_pipeline` |
| All runtime config | Airflow Variables + `rag_pipeline.silver.production_config` |
| MLflow experiments | `/Users/reydencdavies@gmail.com/mlflow/` |