from langgraph.graph import StateGraph, END
from .state import ResearchState
from .nodes import (
    search_web, assess_depth, deep_search,
    extract_info, verify_sources, write_report, route_after_depth
)


def build_research_graph() -> StateGraph:
    builder = StateGraph(ResearchState)

    builder.add_node("search_web", search_web)
    builder.add_node("assess_depth", assess_depth)
    builder.add_node("deep_search", deep_search)
    builder.add_node("extract_info", extract_info)
    builder.add_node("verify_sources", verify_sources)
    builder.add_node("write_report", write_report)

    builder.set_entry_point("search_web")

    builder.add_edge("search_web", "assess_depth")
    builder.add_conditional_edges("assess_depth", route_after_depth, {
        "deep_search": "deep_search",
        "extract_info": "extract_info"
    })
    builder.add_edge("deep_search", "extract_info")
    builder.add_edge("extract_info", "verify_sources")
    builder.add_edge("verify_sources", "write_report")
    builder.add_edge("write_report", END)

    return builder.compile()
