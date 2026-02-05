import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from src.core.llm.openai_llm import OpenAILLM
from src.core.vectorstore.chroma_store import ChromaStore
from src.config import settings
from src.models.codetour_schemas import CodeTour, CodeTourStep
from src.models.database import Repository, CodeFile
from src.models.learning import (
    Lesson,
    LessonContent,
    Module,
    Persona,
    Syllabus,
    GraphNode,
    GraphEdge,
    DependencyGraph,
)

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

        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found for graph generation")
            return None

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

        # Extract file info (cap to avoid oversized prompts)
        max_files = settings.graph_max_files
        available_files = [d.metadata.get("file_path", "unknown") for d in unique_docs[:max_files]]
        available_files = [p for p in available_files if p and p != "unknown"]
        files_list = "\n".join(available_files) if available_files else "No files indexed."

        # Build summaries within a total prompt budget
        summaries = []
        summary_map = {}
        summary_max_chars = settings.graph_summary_max_chars
        prompt_budget = settings.graph_prompt_max_chars
        current_chars = 0

        for d in unique_docs[:max_files]:
            path = d.metadata.get("file_path", "unknown")
            if not path or path == "unknown":
                continue
            content = d.content
            if len(content) > summary_max_chars:
                content = content[:summary_max_chars] + "..."
            summary = f"### {path}\n{content}"
            if current_chars + len(summary) > prompt_budget:
                break
            summaries.append(summary)
            summary_map[path] = content
            current_chars += len(summary) + 2

        context_str = "\n\n".join(summaries)

        # ========== ENHANCED LLM PROMPT ==========
        prompt = f"""You are an expert software architect. Analyze the codebase files below and generate a COMPREHENSIVE dependency graph.

**INSTRUCTIONS**:
1. Include 10-20 nodes representing significant files (not just entry points)
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
7. List key exports (functions, classes, components) for each file (max 3 items)

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

Generate a DENSE but compact graph. Aim for 10-25 edges."""

        messages = [
            {"role": "system", "content": "You are an expert codebase dependency analyzer. Output ONLY valid JSON. Be thorough and include all significant files."},
            {"role": "user", "content": prompt}
        ]

        response = await self._llm.generate(
            messages,
            max_tokens=settings.graph_max_tokens,
            timeout=settings.graph_llm_timeout_seconds,
            temperature=0.1,
            use_cache=False,
        )

        try:
            cleaned = self._extract_json_block(response)
            data = json.loads(cleaned)
        except Exception:
            try:
                repaired = self._repair_json_like(cleaned)
                data = json.loads(repaired)
            except Exception:
                # Final fallback: ask LLM to repair JSON only
                try:
                    fixed = await self._llm.generate(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "You are a strict JSON repair assistant. "
                                    "Return ONLY valid JSON with double quotes and no trailing commas."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Fix the JSON below. Output ONLY valid JSON, no markdown, no comments.\n\n"
                                    f"{cleaned}"
                                ),
                            },
                        ],
                        max_tokens=settings.graph_max_tokens,
                        timeout=settings.graph_llm_timeout_seconds,
                        temperature=0.0,
                        use_cache=False,
                    )
                    fixed_cleaned = self._extract_json_block(fixed)
                    fixed_repaired = self._repair_json_like(fixed_cleaned)
                    data = json.loads(fixed_repaired)
                except Exception as e:
                    logger.error(f"Failed to generate graph: {e}")
                    return None

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

        # If LLM produced invalid/unknown node ids, rebuild nodes deterministically
        all_paths = {f.path for f in self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()}
        valid_nodes = [n for n in nodes if n.id in all_paths]
        if len(valid_nodes) < 2:
            nodes = self._build_nodes_from_repo(repo, all_paths, limit=settings.graph_max_files)
            node_ids = {n.id for n in nodes}
            edges = []

        if len(edges) < settings.graph_min_edges and len(nodes) >= 2:
            extra_edges = await self._generate_edges_only(nodes, summary_map)
            if extra_edges:
                edges = extra_edges

        # Deterministic fallback: parse imports from repo files
        if len(edges) < settings.graph_min_edges and repo.local_path:
            static_edges, extra_nodes = self._build_edges_from_imports(
                repo,
                [n.id for n in nodes],
                max_new_nodes=10,
            )
            if static_edges:
                # Merge edges without duplicates
                seen = {(e.source, e.target, e.type) for e in edges}
                for e in static_edges:
                    key = (e.source, e.target, e.type)
                    if key not in seen:
                        edges.append(e)
                        seen.add(key)

                # Add any extra nodes (minimal metadata)
                for nid in extra_nodes:
                    if nid not in {n.id for n in nodes}:
                        nodes.append(GraphNode(
                            id=nid,
                            label=Path(nid).name,
                            type="file",
                            description="Imported module",
                        ))

        logger.info(f"Generated graph with {len(nodes)} nodes and {len(edges)} edges")
        return DependencyGraph(nodes=nodes, edges=edges)

    async def _generate_edges_only(self, nodes: List[GraphNode], summary_map: dict) -> List[GraphEdge]:
        node_ids = [n.id for n in nodes if n.id]
        if len(node_ids) < 2:
            return []

        hints = []
        for nid in node_ids:
            summary = summary_map.get(nid, "")
            if summary:
                summary = summary.replace("\n", " ")[:120]
                hints.append(f"- {nid}: {summary}")
            else:
                hints.append(f"- {nid}")

        edge_prompt = f"""Generate ONLY edges for a dependency graph.

Use ONLY these node IDs (verbatim):
{chr(10).join(node_ids)}

Hints (file summaries):
{chr(10).join(hints)}

Return ONLY valid JSON in this exact format:
{{
  "edges": [
    {{
      "source": "path/to/source.js",
      "target": "path/to/target.js",
      "label": "imports X",
      "type": "imports|uses|calls|configures|extends",
      "weight": 1
    }}
  ]
}}

Aim for 10-25 edges.
"""

        response = await self._llm.generate(
            [{"role": "system", "content": "Return ONLY JSON."}, {"role": "user", "content": edge_prompt}],
            max_tokens=settings.graph_edge_max_tokens,
            timeout=settings.graph_llm_timeout_seconds,
            temperature=0.0,
            use_cache=False,
        )

        try:
            cleaned = self._extract_json_block(response)
            data = json.loads(cleaned)
        except Exception:
            try:
                repaired = self._repair_json_like(cleaned)
                data = json.loads(repaired)
            except Exception:
                return []

        edges_payload = data.get("edges", data if isinstance(data, list) else [])
        node_id_set = set(node_ids)
        edges = []
        for e in edges_payload or []:
            if e.get("source") in node_id_set and e.get("target") in node_id_set:
                edges.append(GraphEdge(
                    source=e.get("source", ""),
                    target=e.get("target", ""),
                    label=e.get("label", "imports"),
                    type=e.get("type", "imports"),
                    weight=e.get("weight"),
                ))

        return edges

    def _extract_json_block(self, text: str) -> str:
        cleaned = text.replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return cleaned
        return cleaned[start:end + 1]

    def _repair_json_like(self, text: str) -> str:
        # Remove JS-style comments
        no_comments = re.sub(r"//.*?$|/\*.*?\*/", "", text, flags=re.MULTILINE | re.DOTALL)
        # Remove trailing commas
        no_trailing_commas = re.sub(r",\s*([}\]])", r"\1", no_comments)
        # Insert missing commas between object boundaries (best-effort)
        with_commas = re.sub(r"}\s*{", "},{", no_trailing_commas)
        # Convert single-quoted keys/values to double quotes (best-effort)
        single_quoted = re.sub(r"{\s*'([^'\\]*(?:\\.[^'\\]*)*)'\s*:", r'{"\1":', with_commas)
        single_quoted = re.sub(r",\s*'([^'\\]*(?:\\.[^'\\]*)*)'\s*:", r',"\1":', single_quoted)
        single_quoted = re.sub(
            r'(:\s*)\'([^\'\\]*(?:\\.[^\'\\]*)*)\'',
            lambda m: f'{m.group(1)}"{m.group(2).replace(chr(34), r"\\\"")}"',
            single_quoted
        )
        return single_quoted

    def _build_edges_from_imports(
        self,
        repo: Repository,
        node_ids: List[str],
        max_new_nodes: int = 10,
    ) -> tuple[List[GraphEdge], List[str]]:
        repo_root = Path(repo.local_path)
        if not repo_root.exists():
            return [], []

        files = self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
        all_paths = {f.path for f in files}
        node_set = set(node_ids)
        extra_nodes = []
        edges = []
        seen_edges = set()

        for source in node_ids:
            abs_path = repo_root / source
            if not abs_path.exists():
                continue
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            modules = set()
            modules.update(re.findall(r"import\\s+(?:[^;]*?\\s+from\\s+)?[\\\"']([^\\\"']+)[\\\"']", content))
            modules.update(re.findall(r"require\\(\\s*[\\\"']([^\\\"']+)[\\\"']\\s*\\)", content))

            for mod in modules:
                if not mod.startswith("."):
                    continue
                resolved = self._resolve_module_path(source, mod, all_paths)
                if not resolved:
                    continue

                # Allow adding extra nodes if needed
                if resolved not in node_set and len(extra_nodes) < max_new_nodes:
                    extra_nodes.append(resolved)
                    node_set.add(resolved)

                if resolved in node_set:
                    key = (source, resolved, "imports")
                    if key not in seen_edges and source != resolved:
                        edges.append(GraphEdge(
                            source=source,
                            target=resolved,
                            label=f"imports {mod}",
                            type="imports",
                            weight=1,
                        ))
                        seen_edges.add(key)

        return edges, extra_nodes

    def _build_nodes_from_repo(
        self,
        repo: Repository,
        all_paths: set,
        limit: int = 50,
    ) -> List[GraphNode]:
        # Prefer JS/TS files and common entrypoints
        preferred = []
        others = []
        for f in self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all():
            if f.path not in all_paths:
                continue
            path = f.path
            name = Path(path).name.lower()
            score = f.line_count or 0
            if any(k in name for k in ["index.", "app.", "server.", "main.", "router", "route", "config", "middleware"]):
                preferred.append((path, f, score + 500))
            else:
                others.append((path, f, score))

        # Sort by score (line count + importance)
        ranked = sorted(preferred, key=lambda x: x[2], reverse=True)
        ranked += sorted(others, key=lambda x: x[2], reverse=True)

        nodes = []
        for path, f, _ in ranked[:limit]:
            nodes.append(GraphNode(
                id=path,
                label=Path(path).name,
                type=self._classify_path(path),
                description="",
                group=Path(path).parent.name if Path(path).parent.name else None,
                loc=f.line_count,
            ))
        return nodes

    def _classify_path(self, path: str) -> str:
        p = path.lower()
        if "route" in p or "router" in p:
            return "api"
        if "config" in p or "settings" in p:
            return "config"
        if "util" in p or "helper" in p or "common" in p:
            return "util"
        if "middleware" in p:
            return "util"
        if "model" in p or "schema" in p or "types" in p:
            return "schema"
        return "file"
    def _resolve_module_path(self, source_path: str, module_path: str, all_paths: set) -> Optional[str]:
        base_dir = Path(source_path).parent
        candidate = (base_dir / module_path).as_posix()

        # Direct match (with extension already)
        if candidate in all_paths:
            return candidate

        # Try common extensions
        exts = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"]
        for ext in exts:
            if candidate + ext in all_paths:
                return candidate + ext

        # Try index files in a directory
        for ext in exts:
            idx = (Path(candidate) / f"index{ext}").as_posix()
            if idx in all_paths:
                return idx

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
