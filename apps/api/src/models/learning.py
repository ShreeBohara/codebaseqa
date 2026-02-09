from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LessonType(str, Enum):
    CONCEPT = "concept"      # Text conceptual overview
    CODE_TOUR = "code_tour"  # Walkthrough of specific files
    QUIZ = "quiz"            # Interactive check

class Lesson(BaseModel):
    id: str = Field(..., description="Unique slug for the lesson")
    title: str
    description: str
    type: LessonType
    estimated_minutes: int

class Module(BaseModel):
    title: str
    description: str
    lessons: List[Lesson]


class CacheInfo(BaseModel):
    source: str
    generated_at: Optional[str] = None
    expires_at: Optional[str] = None
    prompt_version: Optional[str] = None
    cache_hit: bool = False

class Syllabus(BaseModel):
    repo_id: str
    persona: str  # e.g., "new_hire", "auditor"
    title: str
    description: str
    modules: List[Module]
    quality_meta: Optional[Dict[str, Any]] = None
    cache_info: Optional[CacheInfo] = None

class Persona(BaseModel):
    id: str
    name: str
    description: str
    icon: str

# Lesson Content Models
class CodeReference(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    content: Optional[str] = None
    description: str

class LessonContent(BaseModel):
    id: str
    title: str
    content_markdown: str
    code_references: List[CodeReference]
    diagram_mermaid: Optional[str] = None
    persona: Optional[str] = None
    module_id: Optional[str] = None
    quality_meta: Optional[Dict[str, Any]] = None
    cache_info: Optional[CacheInfo] = None

# Quiz Models
class Question(BaseModel):
    id: str
    text: str
    options: List[str]
    correct_option_index: int
    explanation: str

class Quiz(BaseModel):
    lesson_id: str
    questions: List[Question]

# Dependency Graph Models
class GraphNodeMetrics(BaseModel):
    in_degree: int = 0
    out_degree: int = 0
    degree: int = 0
    centrality: float = 0.0


class GraphNode(BaseModel):
    id: str  # file path
    label: str  # filename
    type: str  # component, page, store, api, util, schema, config, file
    description: str
    entity: Optional[str] = None  # file | module
    # Enhanced fields for richer visualization
    group: Optional[str] = None  # folder/feature cluster (e.g., "components", "pages")
    importance: Optional[int] = None  # 1-10 centrality score
    loc: Optional[int] = None  # estimated lines of code
    exports: Optional[List[str]] = None  # exported functions/classes
    metrics: Optional[GraphNodeMetrics] = None
    module_key: Optional[str] = None
    member_count: Optional[int] = None
    loc_total: Optional[int] = None
    dominant_types: Optional[List[str]] = None
    top_files: Optional[List[str]] = None
    internal_edge_count: Optional[int] = None
    external_edge_count: Optional[int] = None
    internal_density: Optional[float] = None

class GraphEdge(BaseModel):
    source: str
    target: str
    label: str  # human-readable label
    # Enhanced fields
    type: str = "imports"  # imports, uses, extends, calls, configures
    relation: Optional[str] = None
    weight: Optional[int] = None  # relationship strength 1-5
    confidence: Optional[float] = None
    rank: Optional[float] = None
    aggregated_count: Optional[int] = None


class GraphStats(BaseModel):
    nodes: int
    edges: int
    clusters: int
    density: float


class GraphMeta(BaseModel):
    generated_at: str
    source: str  # deterministic | hybrid
    truncated: bool = False
    stats: GraphStats
    view: Optional[str] = None  # file | module
    scope: Optional[str] = None
    recommended_entry: Optional[str] = None  # file | module
    entry_reason: Optional[str] = None
    raw_stats: Optional[GraphStats] = None
    cross_module_ratio: Optional[float] = None
    internal_edges_summarized: Optional[int] = None
    edge_budget: Optional[dict] = None

class DependencyGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    meta: Optional[GraphMeta] = None
