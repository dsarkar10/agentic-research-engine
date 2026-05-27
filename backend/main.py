import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from contextlib import asynccontextmanager

from schemas import ResearchRequest
from graph.graph import build_research_graph
from graph.state import ResearchState
from config import DEEP_MODEL

app = FastAPI(title="Agentic Research Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = await asyncio.to_thread(build_research_graph)
    yield


app.router.lifespan_context = lifespan


def _build_report(raw_text: str, query: str, sources_meta: list, deep_search_used: bool) -> dict:
    try:
        parsed = json.loads(raw_text, strict=False)
        if isinstance(parsed, dict) and "overview" in parsed:
            parsed.setdefault("key_concepts", [])
            parsed.setdefault("code_examples", [])
            parsed.setdefault("tools_and_libraries", [])
            parsed.setdefault("best_practices", [])
            parsed.setdefault("sources", [])
            parsed["metadata"] = {
                "model": DEEP_MODEL,
                "deep_search_used": deep_search_used,
                "sources_count": len(parsed.get("sources", [])),
            }
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "query": query,
        "overview": raw_text,
        "key_concepts": [],
        "code_examples": [],
        "tools_and_libraries": [],
        "best_practices": [],
        "sources": [s if isinstance(s, dict) else {"title": str(s), "url": "", "confidence": "low"} for s in sources_meta],
        "metadata": {
            "model": DEEP_MODEL,
            "deep_search_used": deep_search_used,
            "sources_count": len(sources_meta),
            "error": "Report was not valid JSON",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/research")
async def research(request: ResearchRequest):
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    async def event_generator():
        state: ResearchState = {
            "query": request.query,
            "deep_search_requested": request.deep_search,
            "search_results": [],
            "deep_search_results": [],
            "extracted_info": None,
            "verified_sources": [],
            "report": None,
            "error": None,
        }

        yield {"event": "status", "data": json.dumps({"agent": "coordinator", "message": "Starting research..."})}

        report_buffer = ""
        verified_sources = []
        deep_search_used = request.deep_search

        try:
            async for event in graph.astream_events(state, version="v2"):
                kind = event.get("event", "")
                node = event.get("name", "")

                if kind == "on_chain_start" and node in (
                    "search_web", "assess_depth", "deep_search", "extract_info", "verify_sources", "write_report"
                ):
                    labels = {
                        "search_web": "Searching the web for information...",
                        "assess_depth": "Assessing if deep search is needed...",
                        "deep_search": "Performing deep technical search...",
                        "extract_info": "Extracting key information and code examples...",
                        "verify_sources": "Verifying sources and cross-referencing...",
                        "write_report": "Writing the final research report...",
                    }
                    yield {"event": "status", "data": json.dumps({"agent": node, "message": labels[node]})}

                if kind == "on_chain_stream" and node == "write_report":
                    data = event.get("data", {})
                    chunk = data.get("chunk", {})
                    if isinstance(chunk, dict) and "report" in chunk:
                        text = chunk["report"]
                        if isinstance(text, str):
                            report_buffer += text
                            yield {"event": "report_chunk", "data": json.dumps({"chunk": text})}

                if kind == "on_chain_start" and node == "verify_sources":
                    deep_search_used = state.get("deep_search_requested", False) or request.deep_search

            final_state = None
            async for s in graph.astream(state):
                for node_name, node_state in s.items():
                    final_state = node_state

            if final_state:
                vs = final_state.get("verified_sources", [])
                if isinstance(vs, list):
                    verified_sources = vs

            if report_buffer:
                parsed = _build_report(report_buffer, request.query, verified_sources, deep_search_used)
                yield {"event": "complete", "data": json.dumps(parsed)}
            else:
                yield {"event": "error", "data": json.dumps({"message": "Failed to generate report"})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
