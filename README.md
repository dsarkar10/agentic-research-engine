# Agentic Research Engine

<p align="center">
  <strong>Multi-agent tech research system powered by LangGraph, Groq & DuckDuckGo</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/LangGraph-1.2.2-6C47FF?style=flat-square" alt="LangGraph">
  <img src="https://img.shields.io/badge/Groq-Llama%203.3%2070B-10B981?style=flat-square" alt="Groq">
  <img src="https://img.shields.io/badge/DuckDuckGo-Search-FF6600?style=flat-square" alt="DuckDuckGo">
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=flat-square" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square" alt="React">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License">
</p>

## Abstract

This project presents a production-grade multi-agent research system that automates the end-to-end workflow of technical research: searching the web via **DuckDuckGo**, extracting structured information, cross-verifying sources, and synthesizing a structured **JSON report** — all powered by **Groq's LPU inference** on Llama 3.3 70B. Every agent output is JSON-formatted, making it machine-readable and directly exportable to other AI agents, pipelines, or data stores. The system is built on **LangGraph** for stateful agent orchestration, **Groq** for low-latency LLM inference, and **FastAPI** for the serving layer, with a **React** frontend providing real-time streaming feedback. The architecture follows a directed acyclic graph (DAG) of specialized agents, each responsible for a discrete stage of the research pipeline, enabling modularity, observability, and extensibility.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Technology Stack & Rationale](#technology-stack--rationale)
3. [Agent Workflow Design](#agent-workflow-design)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
   - [Backend Setup](#backend-setup)
   - [Frontend Setup](#frontend-setup)
7. [Running the Application](#running-the-application)
8. [API Reference](#api-reference)
9. [Development Guide](#development-guide)
   - [Adding a New Agent](#adding-a-new-agent)
   - [Modifying the Workflow](#modifying-the-workflow)
   - [Using a Different LLM Provider](#using-a-different-llm-provider)
10. [Production Deployment](#production-deployment)
11. [License](#license)

---

## System Architecture

The system follows a **layered architecture** with three tiers:

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (React)                      │
│  SearchBar → ProgressPanel (SSE stream) → ReportView     │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP/SSE
┌──────────────────────────▼───────────────────────────────┐
│                     Backend (FastAPI)                      │
│  POST /research → SSE event stream → report + sources     │
└──────────────────────────┬───────────────────────────────┘
                           │ Invocation
┌──────────────────────────▼───────────────────────────────┐
│              LangGraph State Machine (DAG)                │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐               │
│  │ Search  │→│ Assess  │→│ Extract  │               │
│  │ Web     │  │ Depth   │  │ Info     │               │
│  └─────────┘  └────┬─────┘  └───────────┘               │
│                    │                                      │
│                    ▼                                      │
│              ┌──────────┐                                │
│              │ Deep     │ (conditional)                  │
│              │ Search   │                                │
│              └──────────┘                                │
│                                        │                  │
│                                        ▼                  │
│                              ┌──────────┐  ┌───────────┐ │
│                              │ Verify   │→│ Write     │ │
│                              │ Sources  │  │ Report    │ │
│                              └──────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Client** sends a POST request with a query to `/research`
2. **FastAPI** instantiates a `ResearchState` and streams it through the LangGraph
3. **LangGraph** executes the DAG nodes sequentially, with a conditional branch at `assess_depth`
4. Each node emits `astream_events` that are forwarded as Server-Sent Events (SSE) to the client
5. The **React frontend** consumes the SSE stream, updating a progress panel in real time and rendering the report incrementally

---

## Technology Stack & Rationale

| Component          | Technology         | Rationale                                                                 |
|--------------------|--------------------|---------------------------------------------------------------------------|
| Agent Orchestration| LangGraph 1.2.2    | Native DAG-based state machine with conditional branching, streaming, and built-in checkpointing. Superior to simple chain-based approaches for multi-step agent workflows. |
| LLM Inference      | Groq (Llama 3.3)   | Blazing-fast inference on Llama 3.3 70B via Groq's LPU hardware. No other provider matches this throughput for open-weight models. |
| Web Search         | DuckDuckGo (free)  | No API key required. Privacy-respecting. Sufficient for tech research. The deep-search fallback uses Groq-generated queries for targeted retrieval. |
| Serving Layer      | FastAPI 0.136.3    | Async-first Python framework with native SSE support via `sse-starlette`. Pydantic v2 for strict request/response validation. |
| Frontend           | React 19 + Vite 6  | Streaming SSE parsing in the browser. `react-markdown` for safe markdown rendering. Dark-theme GitHub-inspired design. |
| Streaming          | SSE                | Server-Sent Events over HTTP. Simpler than WebSockets for unidirectional event streaming. Native `EventSource` API in browsers. |

---

## Agent Workflow Design

The LangGraph state machine (`backend/graph/graph.py`) defines six nodes connected in a directed acyclic graph:

### State Definition (`backend/graph/state.py`)

```python
class ResearchState(TypedDict):
    query: str                    # User's research query
    deep_search_requested: bool   # Toggle for deep search mode
    search_results: list[Source]  # DuckDuckGo search results (accumulated via operator.add)
    deep_search_results: list[Source]  # Results from targeted deep search
    extracted_info: str | None    # Structured extraction from all results
    verified_sources: list[Source]  # Sources after verification pass
    report: str | None            # Final synthesized report
    error: str | None             # Error state for exception handling
```

### Node Descriptions

#### 1. `search_web` — Web Search Agent
- **Tool**: DuckDuckGo search via `duckduckgo_search` SDK
- **Behavior**: Fetches `MAX_SEARCH_RESULTS` (default: 5) results for the raw query
- **Output**: Populates `search_results` with `Source(url, title, snippet)` tuples

#### 2. `assess_depth` — Depth Assessment Agent
- **Model**: `llama-3.3-70b-versatile` (fast model)
- **Prompt**: Given the query and result count, decides if deep search is needed
- **Logic**: Deep search triggers when results are few, the topic requires code examples/API docs, or the user explicitly requested deep mode
- **Output**: Sets `deep_search_requested` boolean
- **Routing**: Conditional edge — `deep_search` or `extract_info`

#### 3. `deep_search` — Deep Search Agent
- **Model**: `llama-3.3-70b-versatile` (deep model)
- **Strategy**: LLM generates 3 targeted search queries based on initial results, then executes DuckDuckGo searches for each (3 results each)
- **Use Case**: Finding specific code examples, official docs, or advanced patterns
- **Output**: Appends to `deep_search_results`

#### 4. `extract_info` — Information Extraction Agent
- **Model**: `llama-3.3-70b-versatile`
- **Input**: Combined `search_results` + `deep_search_results`
- **Task**: Extracts key concepts, code snippets, API names, best practices, and documentation references
- **Output**: Structured string in `extracted_info`

#### 5. `verify_sources` — Source Verification Agent
- **Model**: `llama-3.3-70b-versatile`
- **Task**: Reviews each source for authority (official docs, GitHub, known domains), currency, and code correctness
- **Output**: Confidence-labeled source list in `verified_sources`

#### 6. `write_report` — Report Synthesis Agent
- **Model**: `llama-3.3-70b-versatile`
- **Task**: Composes a structured JSON report with fields: `query`, `overview`, `key_concepts`, `code_examples`, `tools_and_libraries`, `best_practices`, `sources`, `metadata`
- **Output**: JSON string in `report` — validated and parsed into a `ResearchReport` object before returning to the client

### Prompt Engineering Notes

All prompts are stored in `backend/graph/prompts.py` as constants. Key design principles:
- **Role assignment**: Each prompt begins with "You are a [role]" to establish persona
- **JSON output**: The `WRITE_REPORT`, `EXTRACT_INFO`, and `VERIFY_SOURCES` prompts instruct the LLM to output valid JSON with exact field schemas, enabling direct machine consumption
- **Resilient parsing**: The backend uses `json.loads(raw, strict=False)` to handle LLM outputs with unescaped control characters, with a fallback wrapping that preserves the raw text
- **Token efficiency**: The `assess_depth` prompt uses a simple yes/no decision, minimizing token usage

---

## Project Structure

```
langc/
│
├── backend/                          # Python FastAPI backend
│   ├── main.py                       # FastAPI app entry point with SSE endpoint
│   ├── config.py                     # Environment configuration and model selection
│   ├── schemas.py                    # Pydantic request/response models
│   ├── requirements.txt              # Pinned Python dependencies
│   ├── .env.example                  # Environment variable template
│   ├── .env                          # Local environment variables (gitignored)
│   │
│   ├── graph/                        # LangGraph workflow definition
│   │   ├── __init__.py
│   │   ├── state.py                  # TypedDict state definition
│   │   ├── prompts.py                # LLM prompt templates
│   │   ├── nodes.py                  # Agent node implementations
│   │   └── graph.py                  # Graph builder and compilation
│   │
│   └── agents/                       # Agent module (extensible for custom agents)
│       └── __init__.py
│
├── frontend/                         # React TypeScript frontend
│   ├── package.json                  # Node dependencies
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── vite.config.ts                # Vite bundler configuration with API proxy
│   ├── index.html                    # HTML entry point
│   │
│   └── src/
│       ├── main.tsx                  # React entry point
│       ├── App.tsx                   # Root component with research state management
│       ├── index.css                 # Global dark-theme styles
│       │
│       ├── api/
│       │   └── client.ts            # SSE streaming fetch client
│       │
│       └── components/
│           ├── SearchBar.tsx         # Query input form with deep-search toggle
│           ├── ProgressPanel.tsx     # Streaming agent progress display
│           └── ReportView.tsx        # Markdown report renderer
│
├── .gitignore                        # Version control exclusions
└── README.md                         # This file
```

---

## Prerequisites

- **Python** 3.10+ (tested on 3.14)
- **Node.js** 18+ (tested on 24.14)
- **npm** 9+
- **Groq API key** — Free at [console.groq.com](https://console.groq.com) (sign up, create key, free tier has rate limits for Llama 3.1 70B)

The system is cross-platform (macOS, Linux, Windows WSL).

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/dsarkar10/agentic-research-engine.git
cd agentic-research-engine
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment (Python 3.10+ required)
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install all dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Groq API key
# GROQ_API_KEY=gsk_your_key_here
# FAST_MODEL=llama-3.3-70b-versatile      # Fast inference model
# DEEP_MODEL=llama-3.3-70b-versatile      # Deep reasoning model (can be same as fast)
# MAX_SEARCH_RESULTS=5                     # Number of web results per search
```

### 4. Frontend Setup

```bash
# Navigate to frontend
cd ../frontend

# Install Node dependencies
npm install
```

---

## Running the Application

### Development Mode (Recommended)

**Terminal 1 — Backend:**

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`. The `--reload` flag enables hot-reload on code changes.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

The frontend starts at `http://localhost:5173`. Vite proxies `/api/*` requests to the backend at `http://localhost:8000`.

Open `http://localhost:5173` in your browser, enter a tech research query (e.g., "How to implement RAG with LangChain and ChromaDB"), and watch the agents work in real time.

### Production Mode

```bash
# Build frontend
cd frontend && npm run build

# Serve with backend (configure FastAPI to serve static files)
# Or use a reverse proxy (Nginx, Caddy) pointing to port 8000
```

---

## API Reference

### `POST /research`

Initiates a multi-agent research workflow. All output is structured JSON for easy consumption by other AI agents and data pipelines.

**Request Body:**

```json
{
  "query": "How to use LangGraph for multi-agent systems",
  "deep_search": false
}
```

| Field          | Type    | Required | Description                                        |
|----------------|---------|----------|----------------------------------------------------|
| `query`        | string  | Yes      | The technical research topic                       |
| `deep_search`  | boolean | No       | Skip depth assessment and force deep search (default: false) |

**Response:** Server-Sent Events (SSE) stream with `text/event-stream` content type.

**Event Types:**

| Event           | Data Fields                                     | Description                                      |
|-----------------|-------------------------------------------------|--------------------------------------------------|
| `status`        | `{ agent, message }`                            | Agent activity update (shown in progress panel)  |
| `report_chunk`  | `{ chunk }`                                     | Raw JSON text chunks as the LLM generates them   |
| `complete`      | Full `ResearchReport` JSON object (see below)   | Structured JSON report with all sections          |
| `error`         | `{ message }`                                   | Error description                                 |

#### Complete Event — `ResearchReport` JSON Schema

```json
{
  "query": "string — the original research query",

  "overview": "string — 2-3 paragraph overview of the topic",

  "key_concepts": [
    {
      "concept": "string — name of the concept",
      "explanation": "string — detailed technical explanation"
    }
  ],

  "code_examples": [
    {
      "language": "string — e.g. 'python', 'rust', 'typescript'",
      "description": "string — what this example demonstrates",
      "code": "string — actual runnable code with proper syntax"
    }
  ],

  "tools_and_libraries": [
    {
      "name": "string — tool or library name",
      "url": "string — link to official page or repo",
      "description": "string — what it does and why it matters"
    }
  ],

  "best_practices": ["string — actionable recommendation with reasoning"],

  "sources": [
    {
      "title": "string — source title",
      "url": "string — source URL",
      "confidence": "string — one of: 'high', 'medium', 'low'"
    }
  ],

  "metadata": {
    "model": "string — LLM model used for generation",
    "deep_search_used": "boolean — whether deep search was triggered",
    "sources_count": "integer — number of sources in the report",
    "error": "string | null — error message if JSON parsing failed"
  }
}
```

**Example SSE stream:**

```
event: status
data: {"agent": "search_web", "message": "Searching the web for information..."}

event: status
data: {"agent": "extract_info", "message": "Extracting key information and code examples..."}

event: report_chunk
data: {"chunk": "{\n  \"query\": \"How to use LangGraph...\"}}

event: complete
data: {"query": "How to use LangGraph...", "overview": "...", "key_concepts": [...], "code_examples": [...], "tools_and_libraries": [...], "best_practices": [...], "sources": [...], "metadata": {...}}
```

### `GET /health`

Returns `{ "status": "ok" }` for health checks.

---

## Development Guide

### Adding a New Agent

1. **Define the prompt** in `backend/graph/prompts.py`:

```python
MY_AGENT_PROMPT = """You are a [role]. Perform [task] given: {input_var}"""
```

2. **Implement the node** in `backend/graph/nodes.py`:

```python
def my_agent_node(state: ResearchState) -> dict:
    llm = _fast_llm()  # or _deep_llm()
    response = llm.invoke([HumanMessage(content=MY_AGENT_PROMPT.format(
        input_var=state["some_field"]
    ))])
    return {"new_field": response.content}
```

3. **Add the field** to `ResearchState` in `backend/graph/state.py`:

```python
class ResearchState(TypedDict):
    ...
    new_field: str | None
```

4. **Register the node and edge** in `backend/graph/graph.py`:

```python
builder.add_node("my_agent", my_agent_node)
builder.add_edge("previous_node", "my_agent")
builder.add_edge("my_agent", "next_node")
```

### Modifying the Workflow

The workflow DAG is defined in `build_research_graph()`. LangGraph supports:
- **Sequential edges**: `add_edge(from, to)`
- **Conditional edges**: `add_conditional_edges(source, router_func, mapping)`
- **Parallel branches**: Multiple edges from a single node
- **Cycles**: Supported via `add_edge(to, from)` for feedback loops

### Using a Different LLM Provider

Replace the `ChatGroq` instantiation in `backend/graph/nodes.py`:

```python
# For OpenAI:
from langchain_openai import ChatOpenAI
def _fast_llm():
    return ChatOpenAI(model="gpt-4o-mini", api_key="sk-...")

# For Anthropic:
from langchain_anthropic import ChatAnthropic
def _deep_llm():
    return ChatAnthropic(model="claude-sonnet-4-20250514", api_key="sk-...")

# For Ollama (local):
from langchain_ollama import ChatOllama
def _fast_llm():
    return ChatOllama(model="llama3.1:8b")
```

### Running Tests

```bash
# Backend: Python syntax and import checks
cd backend && source .venv/bin/activate
python -c "from graph.graph import build_research_graph; print('Graph compiles:', build_research_graph())"

# Frontend: TypeScript type check
cd frontend && npx tsc --noEmit

# Frontend: Production build
cd frontend && npm run build
```

---

## Production Deployment

### Docker

Create a `Dockerfile` in the project root:

```dockerfile
# Backend
FROM python:3.12-slim AS backend
WORKDIR /app/backend
COPY backend/ .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend (served via nginx or bundled with backend)
FROM node:20 AS frontend
WORKDIR /app/frontend
COPY frontend/ .
RUN npm install && npm run build
```

### Environment Variables (Production)

| Variable            | Required | Default                    | Description                          |
|--------------------|----------|----------------------------|--------------------------------------|
| `GROQ_API_KEY`     | Yes      | —                          | Groq API key                         |
| `FAST_MODEL`       | No       | `llama-3.3-70b-versatile`  | Model for fast assessment nodes      |
| `DEEP_MODEL`       | No       | `llama-3.3-70b-versatile`  | Model for deep extraction/writing    |
| `MAX_SEARCH_RESULTS` | No     | `5`                        | Results per DuckDuckGo search query  |
| `HOST`             | No       | `0.0.0.0`                  | Bind address                         |
| `PORT`             | No       | `8000`                     | Server port                          |

### Scaling Considerations

- **Rate limiting**: Groq's free tier has TPM limits. For production, upgrade to paid tier or swap to OpenAI/Anthropic.
- **Search rate limits**: DuckDuckGo may throttle rapid requests. Add `time.sleep(1)` between calls if needed.
- **State persistence**: LangGraph supports checkpointing via `MemorySaver`, `PostgresSaver`, or `SqliteSaver` for long-running workflows.
- **Caching**: Cache search results for identical queries using Redis or disk-based cache.

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Citation

If you use this project in academic work, please cite:

```bibtex
@software{agentic_research_engine_2026,
  author = {Sarkar, Deep},
  title = {Agentic Research Engine: Multi-Agent Tech Research System with LangGraph, Groq \& DuckDuckGo},
  year = {2026},
  url = {https://github.com/dsarkar10/agentic-research-engine}
}
```
