from pydantic import BaseModel
from typing import Optional


class ResearchRequest(BaseModel):
    query: str
    deep_search: bool = False


class CodeExample(BaseModel):
    language: str
    description: str
    code: str


class KeyConcept(BaseModel):
    concept: str
    explanation: str


class Tool(BaseModel):
    name: str
    url: str
    description: str


class Source(BaseModel):
    title: str
    url: str
    confidence: str = "medium"


class ReportMetadata(BaseModel):
    model: str
    deep_search_used: bool
    sources_count: int
    error: Optional[str] = None


class ResearchReport(BaseModel):
    query: str
    overview: str
    key_concepts: list[KeyConcept]
    code_examples: list[CodeExample]
    tools_and_libraries: list[Tool]
    best_practices: list[str]
    sources: list[Source]
    metadata: ReportMetadata


class ProgressEvent(BaseModel):
    agent: str
    message: str
    detail: Optional[str] = None
