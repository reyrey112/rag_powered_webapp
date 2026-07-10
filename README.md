# Pharma RAG Web Application

A biomedical retrieval web app using a FastAPI backend and Streamlit frontend deployed on Google Cloud Run for grounded question answering and experiment design workflows. This repository contains the application layer that talks to Databricks SQL and Databricks Vector Search, while using Gemini for answer generation and report synthesis.

The implementation combines:

- a FastAPI backend for query and interview endpoints,
- a Streamlit UI for interactive chat and report generation,
- a legacy adapter layer that bridges the web routes to retrieval and interview logic,
- Databricks-backed retrieval and state persistence.

---

## What this project does

The application lets a user ask a biomedical research question and:

- retrieve relevant literature chunks from Databricks Vector Search,
- generate a grounded answer from the retrieved context,
- and optionally run a guided interview that produces a structured experiment-design report.

---

## Architecture

```text
Streamlit UI
    ↓
backend/api_client.py
    ↓
FastAPI backend (backend/main.py)
    ↓
backend/routers/query.py
backend/routers/interview.py
    ↓
backend/legacy/rag_query_sparkless.py
backend/legacy/interview_state.py
backend/legacy/conversation_history.py
    ↓
Databricks SQL + Vector Search + Gemini
```

The app is served through Docker-based FastAPI and Streamlit containers, deployed on Google Cloud Run.

---

## Tech stack

| Layer | Tooling |
|---|---|
| API | FastAPI, Pydantic, Uvicorn |
| Frontend | Streamlit |
| Retrieval | Databricks SQL Connector, Databricks Vector Search |
| Embeddings | Sentence Transformers |
| Generation | Gemini via Google GenAI |
| Deployment | Docker Compose, Google Cloud Run, GitHub Actions |
| Testing | pytest |

---

## Key capabilities

### Standard RAG workflow
Chat retrieval endpoint:

- `POST /query` receives a prompt and session ID,
- loads conversation history,
- enriches the query,
- retrieves relevant chunks,
- and returns a grounded answer with source metadata.

### Interview and experiment-design workflow
Interview endpoints:

- `POST /interview/start`
- `POST /interview/answer`
- `POST /interview/report`
- `POST /interview/should-start`
- `POST /interview/is-greeting`

### Persistence and session handling
The app stores:

- conversation history in `rag_pipeline.silver.conversation_history`,
- interview state in `rag_pipeline.silver.interview_states`,
- production configuration in `rag_pipeline.silver.production_config`.

### Deployment
The project includes Dockerfiles for both the API and Streamlit app, a Compose file for local orchestration, and GitHub Actions for CI/CD to Cloud Run.

---

## Repository structure

```text
rag_powered_webapp/
├── .github/
│   ├── dependabot.yaml
│   └── workflows/
│       └── deploy.yaml
├── backend/
│   ├── Dockerfile
│   ├── __init__.py
│   ├── api_client.py
│   ├── legacy/
│   │   ├── __init__.py
│   │   ├── conversation_history.py
│   │   ├── interview_state.py
│   │   └── rag_query_sparkless.py
│   ├── main.py
│   ├── models/
│   │   ├── requests.py
│   │   └── responses.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── interview.py
│   │   └── query.py
│   ├── services/
│   │   ├── chat_orchestrator.py
│   │   ├── experiment_design_service.py
│   │   ├── interview_service.py
│   │   └── rag_service.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   └── interview_router.py
│   │   ├── integration/
│   │   │   └── test_main.py
│   │   └── unit/
│   │       └── test_interview_state.py
│   └── tools/
│       ├── gemini_call.py
│       └── iterative_retrieval.py
├── frontend/
│   └── streamlit_app.py
├── .dockerignore
├── .gitignore
├── Architecture.md
├── Dockerfile.streamlit
├── README.md
├── compose.yaml
├── production.md
├── pyproject.toml
├── requirements.txt
├── setup.sh
└── uv.lock
```

---

## Main modules

- `backend/main.py` — FastAPI app entrypoint and health check
- `backend/routers/query.py` — standard RAG query route
- `backend/routers/interview.py` — interview-start, answer, report, and detection routes
- `backend/legacy/rag_query_sparkless.py` — retrieval, answer generation, and experiment-design orchestration
- `backend/legacy/interview_state.py` — interview state machine and question generation logic
- `backend/legacy/conversation_history.py` — Databricks backed conversation persistence
- `backend/api_client.py` — HTTP client used by the Streamlit app
- `frontend/streamlit_app.py` — interactive Streamlit UI for chat and report workflows
- `backend/tools/gemini_call.py` — Gemini call wrapper
- `backend/tools/iterative_retrieval.py` — iterative retrieval loop
- `.github/workflows/deploy.yaml` — Cloud Run deploy automation

---

## Local development

### Prerequisites

- Python 3.13+
- Databricks workspace access with the required secrets and environment variables
- Optional: Docker for container based local runs

### Environment variables

Create a local `.env` file at the repository root with values such as:

```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
GEMINI_API_KEY=...
API_BASE_URL=http://localhost:8000
```

### Install dependencies

```bash
uv sync --group api --group frontend --group data-engineering --group dev
```

### Run the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Run the frontend

```bash
cd frontend
streamlit run streamlit_app.py --server.headless true
```

### Run with Docker Compose

```bash
docker compose up --build
```

This starts the FastAPI backend on port `8000` and the Streamlit app on port `8501`.

---

## Notes 

- The backend relies on the compatibility layer in `backend/legacy/` rather than direct notebook or job calls.
- The Streamlit app consumes the backend over HTTP through `backend/api_client.py`.
- The Databricks configuration is pulled from environment variables and the production config table.
- This repository is the web application layer only; it contains the HTTP-facing app and its supporting backend modules.

---

## Testing

Run the backend tests with:

```bash
pytest backend/tests/ -v
```


