# Architecture

This document reflects the current repository layout and implementation.

## Overview

This repository contains a single application layer that exposes a biomedical RAG experience over HTTP:

1. A FastAPI backend that serves query and interview routes.
2. A Streamlit frontend that provides the interactive chat and experiment-design UI.
3. A legacy adapter layer that connects the HTTP routes to retrieval, history, and interview-state logic.

The system follows the current runtime workflow:

1. The user submits a prompt in the Streamlit UI.
2. The UI calls the backend over HTTP through `backend/api_client.py`.
3. The FastAPI routes load or store session state and call the legacy retrieval logic.
4. The adapter uses Databricks SQL and Vector Search to retrieve relevant literature and Gemini to generate answers or report sections.
5. Responses are returned to the UI and stored in Databricks-backed history and interview tables.

This repository is the web application portion of the biomedical RAG system, focused on the FastAPI and Streamlit experience.
See 'pubmed_rag_pipeline' repo for the backend rag pipeline logic.

---

## Repository structure

```text
rag_powered_webapp/
├── .dockerignore
├── .github/
│   ├── dependabot.yaml
│   └── workflows/
│       └── deploy.yaml
├── .gitignore
├── Architecture.md
├── Dockerfile.streamlit
├── README.md
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
├── compose.yaml
├── frontend/
│   └── streamlit_app.py
├── production.md
├── pyproject.toml
├── requirements.txt
├── setup.sh
└── uv.lock
```

Notes:
- The repository contains an application layer only; it includes the FastAPI backend, Streamlit frontend, and supporting legacy retrieval modules.
- The `backend/legacy/` package is the compatibility boundary between the HTTP app and the retrieval logic.

---

## Runtime architecture

### 1. Frontend layer

- `frontend/streamlit_app.py` is the main interactive UI.
- The UI uses `backend/api_client.py` to call the FastAPI routes.
- UI state includes the chat session, interview progress, and report rendering.

### 2. API layer

- `backend/main.py` creates the FastAPI app and mounts the routers.
- `backend/routers/query.py` exposes the main retrieval endpoint.
- `backend/routers/interview.py` exposes the interview lifecycle endpoints.
- `backend/models/requests.py` and `backend/models/responses.py` define the request and response structures.

### 3. Legacy adapter layer

The backend does not call Databricks or retrieval logic directly from the routers. It flows through the compatibility modules under `backend/legacy/`.

- `backend/legacy/rag_query_sparkless.py` handles the retrieval loop and generation path.
- `backend/legacy/interview_state.py` stores the interview state, builds clarifying questions, and helps format the final retrieval query.
- `backend/legacy/conversation_history.py` persists chat turns and session memory to Databricks tables.

The adapter layer keeps the HTTP app decoupled from the low level retrieval implementation.

### 4. Deployment and delivery layer

- `compose.yaml` runs the FastAPI API and Streamlit UI together locally.
- `backend/Dockerfile` builds the API image.
- `Dockerfile.streamlit` builds the Streamlit image.
- `.github/workflows/deploy.yaml` builds and deploys both services to Google Cloud Run after running unit tests.

---

## How the components interact

### Regular RAG request flow
1. The user submits a prompt in the Streamlit UI.
2. The UI calls `backend/api_client.py`.
3. The backend route in `backend/routers/query.py` loads prior history, calls the legacy RAG adapter, writes the turn history, and returns a structured response.
4. The adapter retrieves relevant chunks from Databricks Vector Search and generates an answer using Gemini-backed generation.

### Interview / experiment-design flow
1. The user starts an interview in the Streamlit UI.
2. `backend/routers/interview.py` manages the state machine and calls `backend/legacy/interview_state.py`.
3. The backend asks clarifying questions, stores progress, and later produces a structured experiment design report.
4. The report is returned to the UI for display.

### Persistence flow
1. Conversation turns are written to `rag_pipeline.silver.conversation_history`.
2. Interview progress is written to `rag_pipeline.silver.interview_states`.
3. The latest production model configuration is read from `rag_pipeline.silver.production_config`.

---

## Key modules

### Application modules
- `frontend/streamlit_app.py`
- `backend/main.py`
- `backend/routers/query.py`
- `backend/routers/interview.py`
- `backend/api_client.py`

### Service and model modules
- `backend/services/rag_service.py`
- `backend/services/experiment_design_service.py`
- `backend/services/interview_service.py`
- `backend/models/requests.py`
- `backend/models/responses.py`

### Legacy compatibility modules
- `backend/legacy/rag_query_sparkless.py`
- `backend/legacy/conversation_history.py`
- `backend/legacy/interview_state.py`

### Retrieval and generation helpers
- `backend/tools/gemini_call.py`
- `backend/tools/iterative_retrieval.py`

### Deployment and automation
- `compose.yaml`
- `backend/Dockerfile`
- `Dockerfile.streamlit`
- `.github/workflows/deploy.yaml`

---

## Data model and target tables

The current implementation is designed to work with the following Databricks objects:

- `rag_pipeline.silver.production_config`
- `rag_pipeline.silver.conversation_history`
- `rag_pipeline.silver.interview_states`
- Vector Search endpoint: `rag_pipeline_endpoint`
- Vector Search index: `rag_pipeline.silver.chunk_index`

The production config table is the source of truth for model selection in the query layer.

---

## Configuration and secrets

### Environment variables
- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN`
- `DATABRICKS_HTTP_PATH`
- `GEMINI_API_KEY`
- `API_BASE_URL`

These values are expected to be present in the local `.env` file or in the runtime environment.

### Databricks secrets
- Scope: `rag_pipeline`
- Example secrets: `GEMINI_API_KEY`

---

## Naming conventions

The repository currently follows these conventions:

- Python files: `snake_case.py`
- Python functions: `snake_case`
- Python classes: `PascalCase`
- Constants: `ALL_CAPS`
- Vector Search endpoint: `rag_pipeline_endpoint`
- Vector Search index: `rag_pipeline.silver.chunk_index`

---

## Where to look first

- FastAPI entrypoint: `backend/main.py`
- Standard query route: `backend/routers/query.py`
- Interview route: `backend/routers/interview.py`
- Retrieval adapter: `backend/legacy/rag_query_sparkless.py`
- Interview state: `backend/legacy/interview_state.py`
- History persistence: `backend/legacy/conversation_history.py`
- Streamlit UI: `frontend/streamlit_app.py`
- Deployment workflow: `.github/workflows/deploy.yaml`

---

## Operational handoff notes for future agents

When making changes, identify which layer is affected first:

- If the change is about the HTTP API, inspect the FastAPI routers and models.
- If the change is about retrieval or answer generation, inspect the legacy adapter and tools layer.
- If the change is about the UI experience, inspect the Streamlit app and its API client.
- If the change is about deployment, inspect the Docker files and the GitHub Actions workflow.

### Common gotchas

- The backend uses the legacy adapter modules rather than direct notebook or job invocations.
- The Streamlit app calls the backend over HTTP and does not run retrieval logic in-process.
- Databricks connection details are expected to be present in the environment, not hard-coded in the code.

### Practical local run order

- Local environment bootstrap: `./setup.sh`
- Backend API: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Streamlit UI: `cd frontend && streamlit run streamlit_app.py --server.headless true`
- Docker Compose: `docker compose up --build`

---

## Testing

Run the backend tests with:

```bash
pytest backend/tests/ -v
```

