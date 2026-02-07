import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.core.llm.openai_llm import OpenAILLM
from src.core.vectorstore.chroma_store import ChromaStore
from src.models.codetour_schemas import CodeTour, CodeTourStep
from src.models.database import CodeFile, Repository
from src.models.learning import (
    CodeReference,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    Lesson,
    LessonContent,
    Module,
    Persona,
    Syllabus,
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
        # Code file extensions to include (exclude .md, .txt, etc.)
        CODE_EXTENSIONS = {
            '.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go', '.java', '.c', '.cpp',
            '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.vue',
            '.svelte', '.astro', '.yaml', '.yml', '.json', '.toml', '.sql'
        }

        # 1. Gather Context
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(lesson_title),
            limit=15  # Increased for better context
        )

        # Extract actual file paths from metadata - filter to code files only
        available_files = set()
        for d in context_docs:
            file_path = d.metadata.get("file_path")
            if file_path:
                ext = Path(file_path).suffix.lower()
                if ext in CODE_EXTENSIONS:
                    available_files.add(file_path)

        files_list = "\n".join(sorted(available_files)) if available_files else "No code files indexed."
        context_str = "\n\n---\n\n".join([f"File: {d.metadata.get('file_path', 'unknown')}\n{d.content[:2000]}" for d in context_docs])

        # 2. Build Enhanced Prompt with structure requirements
        prompt = f"""You are an expert technical instructor creating an in-depth lesson titled "{lesson_title}" for this codebase.

## Requirements:
1. **Opening Hook** (2-3 sentences): Why this topic matters, real-world relevance
2. **Learning Objectives**: 3-5 bullet points of what the student will understand
3. **Core Concepts**: 3-5 detailed sections explaining the topic with specific code references
4. **How It Works Here**: Explain how this concept is implemented in THIS specific codebase
5. **Common Pitfalls**: 2-3 mistakes to avoid when working with this code
6. **Summary**: Key takeaways in a concise list

## Style Guidelines:
- Be specific to THIS codebase, avoid generic explanations
- Minimum 600 words of content
- Use markdown formatting (headers, bold, lists)
- Reference specific files and explain WHY they matter
- Do NOT include code blocks in content_markdown - use code_references instead

## Available Code Files (use ONLY these for code_references):
{files_list}

## Codebase Context:
{context_str}

Return clean JSON:
{{
  "content_markdown": "Rich, structured lesson content following the requirements above (min 600 words)",
  "code_references": [
    {{
      "file_path": "MUST be from Available Code Files list",
      "start_line": 1,
      "end_line": 30,
      "description": "What to look for and WHY it's important"
    }}
  ],
  "diagram_mermaid": "graph TD; A-->B; (Optional architecture/flow diagram)"
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

            # Post-process code references - filter to code files only
            raw_refs = data.get("code_references", [])
            filtered_refs = []
            for r in raw_refs:
                file_path = r.get("file_path", "")
                ext = Path(file_path).suffix.lower() if file_path else ""
                if ext in CODE_EXTENSIONS:
                    filtered_refs.append(CodeReference(**r))

            return LessonContent(
                id=lesson_id,
                title=lesson_title,
                content_markdown=data.get("content_markdown", "No content generated."),
                code_references=filtered_refs,
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
        prompt = f"""You are an expert software architect. Analyze the codebase files below and generate a WELL-CONNECTED dependency graph.

**CRITICAL RULES**:
- EVERY node must have AT LEAST 2 edges (connections)
- NEVER include isolated/orphan files with no connections
- Focus on files that import OR are imported by others
- Target 15-30 edges total, minimum 10 nodes

**RELATIONSHIP TYPES** (use multiple per node):
- "imports" = direct import/require statement
- "uses" = uses functionality, calls functions
- "extends" = class/interface extension
- "configures" = provides config/context to

**NODE SELECTION PRIORITY**:
1. Entry points (index, app, main, layout)
2. Shared components used by multiple files
3. Utility/helper files imported by many
4. API routes and data layers
5. Config files that affect many modules

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
      "description": "What this file does",
      "group": "folder-name",
      "importance": 8
    }}
  ],
  "edges": [
    {{
      "source": "path/to/source.tsx",
      "target": "path/to/target.tsx",
      "label": "imports X",
      "type": "imports"
    }}
  ]
}}

REMEMBER: Dense, connected graph. No orphan nodes. At least 15 edges."""

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
            nodes = self._build_nodes_from_repo(repo, all_paths, limit=settings.graph_max_files, code_only=True)
            node_ids = {n.id for n in nodes}
            edges = []

        # If model produced sparse/no edges, switch to deterministic code-focused nodes
        if len(edges) < settings.graph_min_edges:
            nodes = self._build_nodes_from_repo(repo, all_paths, limit=settings.graph_max_files, code_only=True)
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
                max_new_nodes=20,  # Increased for better coverage
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

        # Filter out orphan nodes (nodes with no connections)
        if not settings.graph_include_orphans:
            nodes, edges = self._filter_connected_nodes(nodes, edges)

        logger.info(f"Generated graph with {len(nodes)} nodes and {len(edges)} edges")
        return DependencyGraph(nodes=nodes, edges=edges)

    def _filter_connected_nodes(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Remove nodes that have no edges (orphans)."""
        connected_ids = set()
        for e in edges:
            connected_ids.add(e.source)
            connected_ids.add(e.target)

        filtered_nodes = [n for n in nodes if n.id in connected_ids]

        # Log if we filtered any
        removed = len(nodes) - len(filtered_nodes)
        if removed > 0:
            logger.info(f"Filtered out {removed} orphan nodes")

        return filtered_nodes, edges

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

        def _replace_single_quoted_value(match: re.Match[str]) -> str:
            escaped = match.group(2).replace('"', '\\"')
            return f'{match.group(1)}"{escaped}"'

        single_quoted = re.sub(
            r'(:\s*)\'([^\'\\]*(?:\\.[^\'\\]*)*)\'',
            _replace_single_quoted_value,
            single_quoted
        )
        return single_quoted

    # Comprehensive import patterns for JS/TS/Python
    IMPORT_PATTERNS = [
        # ESM static imports: import X from "Y", import "Y", import { X } from "Y"
        r'import\s+(?:[^;]*?\s+from\s+)?["\']([^"\']+)["\']',
        # CommonJS require: require("Y"), require('Y')
        r'require\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # Dynamic imports: import("Y"), import('Y')
        r'import\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # Re-exports: export * from "Y", export { X } from "Y"
        r'export\s+\*\s+from\s+["\']([^"\']+)["\']',
        r'export\s+\{[^}]*\}\s+from\s+["\']([^"\']+)["\']',
        # Python: from X import Y
        r'^from\s+(\S+)\s+import',
        # Python: import X
        r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
    ]

    def _build_edges_from_imports(
        self,
        repo: Repository,
        node_ids: List[str],
        max_new_nodes: int = 15,
    ) -> tuple[List[GraphEdge], List[str]]:
        """Build edges by parsing actual import statements from source files."""
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

            # Collect all imports using comprehensive patterns
            modules = set()
            for pattern in self.IMPORT_PATTERNS:
                matches = re.findall(pattern, content, re.MULTILINE)
                modules.update(matches)

            for mod in modules:
                # Skip node_modules and external packages
                if mod.startswith(("node_modules", "http", "https")) or not mod:
                    continue
                # Skip bare package names (no path separator and no relative marker)
                if "/" not in mod and not mod.startswith(".") and "@" not in mod:
                    # Could be external package like "react", "lodash"
                    continue

                resolved = self._resolve_module_path(source, mod, all_paths, repo_root)
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
                            label=f"imports {Path(mod).name or mod}",
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
        code_only: bool = True,
    ) -> List[GraphNode]:
        # Prefer JS/TS files and common entrypoints
        code_exts = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
        preferred = []
        others = []
        for f in self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all():
            if f.path not in all_paths:
                continue
            path = f.path
            ext = Path(path).suffix.lower()
            if code_only and ext not in code_exts:
                continue
            name = Path(path).name.lower()
            score = f.line_count or 0
            if any(k in name for k in ["index.", "app.", "server.", "main.", "router", "route", "config", "middleware"]):
                preferred.append((path, f, score + 500))
            else:
                others.append((path, f, score))

        # Fallback to all files if code-only filter yields nothing
        if not preferred and not others and code_only:
            return self._build_nodes_from_repo(repo, all_paths, limit=limit, code_only=False)

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
    def _resolve_module_path(
        self,
        source_path: str,
        module_path: str,
        all_paths: set,
        repo_root: Path,
    ) -> Optional[str]:
        """
        Resolve import/require targets to repo-relative paths that exist in CodeFile list.
        Handles:
        - relative imports ("./foo", "../bar")
        - Next/TS alias "@/" -> repo root
        - root-relative "/foo/bar" -> repo root
        - bare paths treated as repo-root relative (best-effort)
        """
        base_dir = Path(source_path).parent

        # Normalize aliases
        mod = module_path
        if mod.startswith("@/"):
            mod = mod[2:]  # drop "@/"
        elif mod.startswith("/"):
            mod = mod[1:]

        candidates = []

        # Relative path from current file
        if module_path.startswith("."):
            candidates.append((base_dir / module_path).as_posix())
        else:
            # Treat as repo-root relative
            candidates.append((repo_root / mod).as_posix().replace(repo_root.as_posix() + "/", ""))
            # Also try as-is for already relative strings
            candidates.append(mod)

        exts = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"]

        for cand in candidates:
            # Direct match
            if cand in all_paths:
                return cand
            # Try with extensions
            for ext in exts:
                if cand + ext in all_paths:
                    return cand + ext
            # Try index files inside folder
            for ext in exts:
                idx = (Path(cand) / f"index{ext}").as_posix()
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
