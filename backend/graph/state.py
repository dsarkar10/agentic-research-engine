from typing import TypedDict, Optional, Annotated
import operator


class Source(TypedDict):
    url: str
    title: str
    snippet: str


class ResearchState(TypedDict):
    query: str
    deep_search_requested: bool
    search_results: Annotated[list[Source], operator.add]
    deep_search_results: Annotated[list[Source], operator.add]
    extracted_info: Optional[str]
    verified_sources: list[Source]
    report: Optional[str]
    error: Optional[str]
