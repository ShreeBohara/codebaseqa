from enum import Enum
from typing import List, Optional
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

class Syllabus(BaseModel):
    repo_id: str
    persona: str  # e.g., "new_hire", "auditor"
    title: str
    description: str
    modules: List[Module]

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
class GraphNode(BaseModel):
    id: str  # file path
    label: str  # filename
    type: str  # component, page, store, api, util, schema, config, file
    description: str
    # Enhanced fields for richer visualization
    group: Optional[str] = None  # folder/feature cluster (e.g., "components", "pages")
    importance: Optional[int] = None  # 1-10 centrality score
    loc: Optional[int] = None  # estimated lines of code
    exports: Optional[List[str]] = None  # exported functions/classes

class GraphEdge(BaseModel):
    source: str
    target: str
    label: str  # human-readable label
    # Enhanced fields
    type: str = "imports"  # imports, uses, extends, calls, configures
    weight: Optional[int] = None  # relationship strength 1-5

class DependencyGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
