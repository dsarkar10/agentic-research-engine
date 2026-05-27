import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from duckduckgo_search import DDGS
from .state import ResearchState, Source
from .prompts import ASSESS_DEPTH, EXTRACT_INFO, VERIFY_SOURCES, WRITE_REPORT, DEEP_SEARCH_QUERIES
from config import GROQ_API_KEY, FAST_MODEL, DEEP_MODEL, MAX_SEARCH_RESULTS


def _fast_llm():
    return ChatGroq(model=FAST_MODEL, api_key=GROQ_API_KEY, temperature=0)


def _deep_llm():
    return ChatGroq(model=DEEP_MODEL, api_key=GROQ_API_KEY, temperature=0.3)


def search_web(state: ResearchState) -> dict:
    query = state["query"]
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=MAX_SEARCH_RESULTS):
                results.append(Source(url=r.get("href", ""), title=r.get("title", ""), snippet=r.get("body", "")))
    except Exception as e:
        return {"search_results": [], "error": f"Search failed: {e}"}
    return {"search_results": results, "error": None}


def assess_depth(state: ResearchState) -> dict:
    num_results = len(state.get("search_results", []))
    if state.get("deep_search_requested"):
        return {"deep_search_requested": True}
    llm = _fast_llm()
    response = llm.invoke([HumanMessage(content=ASSESS_DEPTH.format(query=state["query"], num_results=num_results))])
    needs_deep = response.content.strip().lower() == "yes"
    return {"deep_search_requested": needs_deep}


def deep_search(state: ResearchState) -> dict:
    llm = _deep_llm()
    results_text = "\n".join(f"- {s['title']}: {s['snippet']}" for s in state["search_results"])
    response = llm.invoke([HumanMessage(content=DEEP_SEARCH_QUERIES.format(query=state["query"], results=results_text))])
    queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()][:3]
    deep_results = []
    for q in queries:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=3):
                    deep_results.append(Source(url=r.get("href", ""), title=r.get("title", ""), snippet=r.get("body", "")))
        except:
            pass
    return {"deep_search_results": deep_results, "error": None}


def extract_info(state: ResearchState) -> dict:
    all_results = state.get("search_results", []) + state.get("deep_search_results", [])
    results_text = "\n".join(f"[{s['title']}]({s['url']}): {s['snippet']}" for s in all_results)
    llm = _deep_llm()
    response = llm.invoke([HumanMessage(content=EXTRACT_INFO.format(query=state["query"], results=results_text))])
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()
    return {"extracted_info": content}


def verify_sources(state: ResearchState) -> dict:
    all_sources = state.get("search_results", []) + state.get("deep_search_results", [])
    sources_text = "\n".join(f"- {s['title']} ({s['url']})" for s in all_sources)
    extracted = state.get("extracted_info", "")
    llm = _deep_llm()
    response = llm.invoke([HumanMessage(content=VERIFY_SOURCES.format(
        query=state["query"],
        extracted_info=extracted,
        sources=sources_text
    ))])
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()
    try:
        verified = json.loads(content)
        return {"verified_sources": verified if isinstance(verified, list) else all_sources, "error": None}
    except json.JSONDecodeError:
        return {"verified_sources": all_sources, "error": None}


def write_report(state: ResearchState) -> dict:
    verified = state.get("verified_sources", [])
    verified_text = "\n".join(
        f"- {s.get('title', s) if isinstance(s, dict) else s} ({s.get('url', '') if isinstance(s, dict) else ''})"
        for s in verified
    )
    llm = _deep_llm()
    response = llm.invoke([HumanMessage(content=WRITE_REPORT.format(
        query=state["query"],
        extracted_info=state.get("extracted_info", ""),
        verified_sources=verified_text
    ))])
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()
    return {"report": content}


def route_after_depth(state: ResearchState) -> str:
    if state.get("deep_search_requested"):
        return "deep_search"
    return "extract_info"
