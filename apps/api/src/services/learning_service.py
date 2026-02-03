import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from src.core.llm.openai_llm import OpenAILLM
from src.core.vectorstore.chroma_store import ChromaStore
from src.models.codetour_schemas import CodeTour, CodeTourStep
from src.models.database import Repository
from src.models.learning import Lesson, LessonContent, Module, Persona, Syllabus

logger = logging.getLogger(__name__)

class LearningService:
    def __init__(self, db: Session, llm: OpenAILLM, vector_store: ChromaStore):
        self._db = db
        self._llm = llm
        self._vector_store = vector_store

    def get_personas(self) -> List[Persona]:
        """Return available learning personas."""
        return [
            Persona(
                id="new_hire",
                name="The New Hire",
                description="Just joined the team? Get up to speed on architecture, setup, and key conventions.",
                icon="🎓"
            ),
            Persona(
                id="auditor",
                name="The Security Auditor",
                description="Focus on authentication, authorization, API endpoints, and data validation.",
                icon="🔒"
            ),
            Persona(
                id="fullstack",
                name="The Full Stack Dev",
                description="Deep dive into how the frontend connects to the backend and database.",
                icon="⚡"
            ),
            Persona(
                id="archaeologist",
                name="The Archaeologist",
                description="Explore the history, legacy modules, and core design decisions.",
                icon="🏺"
            )
        ]

    async def generate_curriculum(self, repo_id: str, persona_id: str) -> Syllabus:
        """Generate a personalized syllabus for the repository."""
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        persona = next((p for p in self.get_personas() if p.id == persona_id), self.get_personas()[0])

        # 1. Gather Context (README + File Summaries)
        # Search for high-level concepts to ground the syllabus
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query("architecture overview project structure"),
            limit=20
        )

        # Filter for file summaries if possible, or just use what we got
        summaries = []
        for result in context_docs:
            doc = result.content
            if len(doc) < 1000: # Keep it brief
                summaries.append(doc)
            else:
                summaries.append(doc[:1000] + "...")

        context_str = "\n---\n".join(summaries)

        # 2. Build Prompt
        prompt = f"""
You are an expert developer creating a university-style course for a new codebase.
Target Audience: {persona.name} ({persona.description})
Repository: {repo.github_owner}/{repo.github_name}

Based on the code snippets below, create a 4-module syllabus that takes the student from "Zero" to "Hero".
Each module must have 2-4 lessons.

Context from codebase:
{context_str}

Return clean JSON matching this structure:
{{
  "title": "Course Title",
  "description": "Course description",
  "modules": [
    {{
      "title": "Module Title",
      "description": "Module description",
      "lessons": [
        {{
          "id": "slug-id",
          "title": "Lesson Title",
          "description": "One sentence on what this covers",
          "type": "concept",
          "estimated_minutes": 10
        }}
      ]
    }}
  ]
}}
"""

        # 3. Generate
        s_prompt = "You are a curriculum designer. Output valid JSON only."
        messages = [
            {"role": "system", "content": s_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self._llm.generate(messages)

        try:
            # Clean response (remove markdown code blocks if any)
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            return Syllabus(
                repo_id=repo_id,
                persona=persona_id,
                title=data.get("title", f"Course: {repo.github_name}"),
                description=data.get("description", "AI Generated Course"),
                modules=[
                    Module(
                        title=m.get("title"),
                        description=m.get("description"),
                        lessons=[
                            Lesson(**lesson_data) for lesson_data in m.get("lessons", [])
                        ]
                    ) for m in data.get("modules", [])
                ]
            )
        except Exception as e:
            logger.error(f"Failed to generate curriculum: {e}")
            # Fallback
            return Syllabus(
                repo_id=repo_id,
                persona=persona_id,
                title="Generation Failed",
                description="Could not generate curriculum. Please try again.",
                modules=[]
            )

    async def generate_lesson(self, repo_id: str, lesson_id: str, lesson_title: str) -> Optional[LessonContent]:
        """Generate detailed content for a specific lesson."""
        from src.models.learning import CodeReference

        # 1. Gather Context
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(lesson_title),
            limit=10
        )

        # Extract actual file paths from metadata
        available_files = set()
        for d in context_docs:
            file_path = d.metadata.get("file_path")
            if file_path:
                available_files.add(file_path)

        files_list = "\n".join(sorted(available_files)) if available_files else "No files indexed."
        context_str = "\n".join([d.content[:1500] for d in context_docs])

        # 2. Build Prompt with explicit file list
        prompt = f"""
You are an expert technical instructor. Create a lesson titled "{lesson_title}" for this codebase.
Use the provided code context to explain the concepts and point to specific files.
Crucially, include a "Code Tour" where you reference specific files and line numbers (approximate lines are fine).

**CRITICAL**: You MUST ONLY use file paths from the "Available Files" list below. Do NOT invent or guess file paths.

Available Files:
{files_list}

Context:
{context_str}

Return clean JSON:
{{
  "content_markdown": "Full explanation in markdown. Use bolding and lists. Do NOT include code blocks here, point to the code references instead.",
  "code_references": [
    {{
      "file_path": "MUST be from Available Files list above",
      "start_line": 1,
      "end_line": 20,
      "description": "Explanation of what to look for here"
    }}
  ],
  "diagram_mermaid": "graph TD; A-->B; (Optional mermaid diagram source)"
}}
"""

        # 3. Generate
        messages = [
            {"role": "system", "content": "You are a coding instructor. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        response = await self._llm.generate(messages)

        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            # Post-process code references to try and verify lines (optional, skipped for speed)

            return LessonContent(
                id=lesson_id,
                title=lesson_title,
                content_markdown=data.get("content_markdown", "No content generated."),
                code_references=[CodeReference(**r) for r in data.get("code_references", [])],
                diagram_mermaid=data.get("diagram_mermaid")
            )
        except Exception as e:
            logger.error(f"Failed to generate lesson: {e}")
            return None

    async def generate_quiz(self, repo_id: str, lesson_id: str, context_content: str) -> Optional[object]:
        """Generate a quiz validation for a lesson."""
        from src.models.learning import Question, Quiz

        prompt = f"""
You are a creative technical instructor.
Based on the following lesson content, generate 3 multiple-choice questions to test the student's understanding.
Questions should check for conceptual understanding, not just trivia.

Lesson Content:
{context_content[:2000]}...

Return clean JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "text": "Question text here",
      "options": ["Wrong Answer", "Correct Answer", "Wrong Answer", "Wrong Answer"],
      "correct_option_index": 1,
      "explanation": "Why this is correct"
    }}
  ]
}}
"""
        messages = [
            {"role": "system", "content": "You are a quiz generator. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        response = await self._llm.generate(messages)

        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            return Quiz(
                lesson_id=lesson_id,
                questions=[Question(**q) for q in data.get("questions", [])]
            )
        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}")
            return None

    async def generate_graph(self, repo_id: str) -> Optional[object]:
        """Generate a comprehensive, high-quality dependency graph for the repository."""
        from src.models.learning import DependencyGraph, GraphEdge, GraphNode

        # ========== MULTI-QUERY CONTEXT GATHERING ==========
        # Query 1: Core architecture files
        arch_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(
                "main entry point app configuration routing layout index"
            ),
            limit=30
        )

        # Query 2: Components and UI
        ui_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(
                "component page view template layout header footer navigation"
            ),
            limit=30
        )

        # Query 3: Data, state, and API
        data_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(
                "store state context api fetch database schema model types"
            ),
            limit=30
        )

        # Query 4: Utilities and helpers
        util_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(
                "utility helper function hooks lib utils common shared"
            ),
            limit=20
        )

        # Combine and deduplicate by file path
        all_docs = arch_docs + ui_docs + data_docs + util_docs
        seen_paths = set()
        unique_docs = []
        for d in all_docs:
            path = d.metadata.get("file_path", "unknown")
            if path and path != "unknown" and path not in seen_paths:
                seen_paths.add(path)
                unique_docs.append(d)

        # Extract file info
        available_files = sorted(list(seen_paths))
        files_list = "\n".join(available_files) if available_files else "No files indexed."

        # Build detailed summaries
        summaries = []
        for d in unique_docs[:60]:  # Limit to avoid token overflow
            path = d.metadata.get("file_path", "unknown")
            content = d.content[:400] + "..." if len(d.content) > 400 else d.content
            summaries.append(f"### {path}\n{content}")

        context_str = "\n\n".join(summaries)

        # ========== ENHANCED LLM PROMPT ==========
        prompt = f"""You are an expert software architect. Analyze the codebase files below and generate a COMPREHENSIVE dependency graph.

**INSTRUCTIONS**:
1. Include 15-30 nodes representing ALL significant files (not just entry points)
2. Use ONLY file paths from the "Available Files" list as node IDs
3. Group nodes by their folder/feature (e.g., "components", "pages", "api", "utils", "store")
4. Identify MULTIPLE relationship types between files:
   - "imports" = direct import statement
   - "uses" = uses functionality from another file
   - "extends" = class extension or interface implementation
   - "calls" = function call relationship
   - "configures" = configuration dependency
5. Rate each node's importance (1-10) based on how central it is:
   - 10 = core entry point, used by everything
   - 7-9 = major component, many dependencies
   - 4-6 = regular file with some connections
   - 1-3 = leaf file, minimal connections
6. Estimate lines of code (LOC) for each file (50-500 range)
7. List key exports (functions, classes, components) for each file

Available Files:
{files_list}

File Summaries:
{context_str}

Return ONLY valid JSON in this exact format:
{{
  "nodes": [
    {{
      "id": "exact/path/from/list.tsx",
      "label": "filename.tsx",
      "type": "component|page|store|api|util|schema|config",
      "description": "Brief description of what this file does",
      "group": "folder-name",
      "importance": 8,
      "loc": 150,
      "exports": ["ComponentName", "useHook", "helperFn"]
    }}
  ],
  "edges": [
    {{
      "source": "path/to/source.tsx",
      "target": "path/to/target.tsx",
      "label": "imports Button component",
      "type": "imports",
      "weight": 3
    }}
  ]
}}

Generate a DENSE graph with many connections. Aim for 20-40 edges minimum."""

        messages = [
            {"role": "system", "content": "You are an expert codebase dependency analyzer. Output ONLY valid JSON. Be thorough and include all significant files."},
            {"role": "user", "content": prompt}
        ]

        response = await self._llm.generate(messages)

        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

            # Validate nodes have required fields
            nodes = []
            for n in data.get("nodes", []):
                node = GraphNode(
                    id=n.get("id", ""),
                    label=n.get("label", n.get("id", "").split("/")[-1]),
                    type=n.get("type", "file"),
                    description=n.get("description", ""),
                    group=n.get("group"),
                    importance=n.get("importance"),
                    loc=n.get("loc"),
                    exports=n.get("exports")
                )
                nodes.append(node)

            # Validate edges
            node_ids = {n.id for n in nodes}
            edges = []
            for e in data.get("edges", []):
                if e.get("source") in node_ids and e.get("target") in node_ids:
                    edge = GraphEdge(
                        source=e.get("source", ""),
                        target=e.get("target", ""),
                        label=e.get("label", "imports"),
                        type=e.get("type", "imports"),
                        weight=e.get("weight")
                    )
                    edges.append(edge)

            logger.info(f"Generated graph with {len(nodes)} nodes and {len(edges)} edges")
            return DependencyGraph(nodes=nodes, edges=edges)

        except Exception as e:
            logger.error(f"Failed to generate graph: {e}")
            return None

    async def export_lesson_to_codetour(self, repo_id: str, lesson_id: str) -> Optional[CodeTour]:
        """Export a lesson as a VS Code CodeTour."""
        # 1. Find the lesson title from the cached syllabus
        # We search all syllabi for this repo to find the lesson
        from src.models.database import LearningSyllabus as DBSyllabus

        syllabi = self._db.query(DBSyllabus).filter(DBSyllabus.repository_id == repo_id).all()
        lesson_title = None

        for s in syllabi:
            data = s.syllabus_json
            for module in data.get("modules", []):
                for lesson in module.get("lessons", []):
                    if lesson.get("id") == lesson_id:
                        lesson_title = lesson.get("title")
                        break
                if lesson_title:
                    break
            if lesson_title:
                break

        if not lesson_title:
            # Fallback: Try to generate or just use a generic title
            lesson_title = f"Lesson {lesson_id}"

        # 2. Generate (or re-generate) the content
        # Note: In a production app, we should cache the LessonContent in the DB to ensure consistency
        content = await self.generate_lesson(repo_id, lesson_id, lesson_title)

        if not content:
            return None

        # 3. Convert to CodeTour
        steps = []
        for ref in content.code_references:
            steps.append(CodeTourStep(
                file=ref.file_path,
                line=ref.start_line,
                description=f"### {ref.description}\n\nRelated to: {lesson_title}",
                title=lesson_title
            ))

        if not steps:
            # Create a "Intro" step if no code references
            steps.append(CodeTourStep(
                file="README.md",
                line=1,
                description=f"Welcome to **{lesson_title}**.\n\n{content.content_markdown[:200]}...",
                title="Introduction"
            ))

        return CodeTour(
            title=lesson_title,
            steps=steps
        )
