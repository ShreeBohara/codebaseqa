import json
import logging
import posixpath
import re
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from math import log1p
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from src.config import settings
from src.core.llm.openai_llm import OpenAILLM
from src.core.vectorstore.chroma_store import ChromaStore
from src.models.codetour_schemas import CodeTour, CodeTourStep
from src.models.database import CodeFile, LearningLesson, LearningSyllabus, Repository
from src.models.learning import (
    CacheInfo,
    CodeReference,
    DependencyGraph,
    GraphEdge,
    GraphMeta,
    GraphNode,
    GraphNodeMetrics,
    GraphStats,
    Lesson,
    LessonContent,
    Module,
    Persona,
    Syllabus,
)

logger = logging.getLogger(__name__)

class LearningService:
    _graph_cache: Dict[str, Tuple[float, DependencyGraph]] = {}
    _graph_cache_lock = RLock()
    LESSON_CODE_EXTENSIONS = {
        ".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", ".java", ".c", ".cpp",
        ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".vue",
        ".svelte", ".astro", ".yaml", ".yml", ".json", ".toml", ".sql",
    }
    REQUIRED_LESSON_SECTIONS = [
        "mission brief",
        "objectives",
        "architecture walkthrough",
        "code deep dive",
        "pitfalls",
        "recap",
    ]
    PERSONA_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
        "new_hire": {
            "retrieval_query": "onboarding architecture setup conventions workflow entrypoints",
            "tone": "clear, step-by-step, confidence building",
            "mission": "Help the learner become productive with safe first contributions.",
            "pillars": ["project structure", "dev setup", "key patterns", "first delivery path"],
            "relevance_terms": ["onboarding", "convention", "entrypoint", "setup", "workflow"],
        },
        "auditor": {
            "retrieval_query": "authentication authorization validation security middleware secrets compliance",
            "tone": "risk-focused, evidence-first, precise",
            "mission": "Help the learner audit trust boundaries and high-risk flows quickly.",
            "pillars": ["auth boundaries", "input validation", "sensitive data flow", "vulnerability hotspots"],
            "relevance_terms": ["auth", "authorization", "validation", "threat", "risk", "security"],
        },
        "fullstack": {
            "retrieval_query": "frontend backend api database integration state management data flow",
            "tone": "systems-oriented, integration-heavy, practical",
            "mission": "Help the learner understand end-to-end feature delivery across the stack.",
            "pillars": ["ui flow", "api contracts", "persistence layer", "deployment/runtime considerations"],
            "relevance_terms": ["frontend", "backend", "api", "database", "integration", "state"],
        },
        "archaeologist": {
            "retrieval_query": "legacy modules history migration debt architecture evolution backwards compatibility",
            "tone": "forensic, context-rich, decision-history aware",
            "mission": "Help the learner reconstruct why the system evolved and where debt accumulates.",
            "pillars": ["legacy hotspots", "evolution path", "design tradeoffs", "debt containment"],
            "relevance_terms": ["legacy", "migration", "history", "tradeoff", "debt", "compatibility"],
        },
    }

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

    async def generate_curriculum(
        self,
        repo_id: str,
        persona_id: str,
        force_regenerate: bool = False,
        include_quality_meta: bool = False,
    ) -> Syllabus:
        """Generate a personalized syllabus for the repository."""
        if not settings.learning_v2_enabled:
            return await self._generate_curriculum_v1(repo_id, persona_id)

        try:
            return await self._generate_curriculum_v2(
                repo_id,
                persona_id,
                force_regenerate=force_regenerate,
                include_quality_meta=include_quality_meta,
            )
        except Exception as exc:
            logger.error("Learning V2 curriculum failed, falling back to V1: %s", exc)
            return await self._generate_curriculum_v1(repo_id, persona_id)

    async def _generate_curriculum_v1(self, repo_id: str, persona_id: str) -> Syllabus:
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        persona = next((p for p in self.get_personas() if p.id == persona_id), self.get_personas()[0])

        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query("architecture overview project structure"),
            limit=20,
        )

        summaries: List[str] = []
        for result in context_docs:
            doc = result.content
            summaries.append(doc if len(doc) < 1000 else doc[:1000] + "...")

        context_str = "\n---\n".join(summaries)
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
        messages = [
            {"role": "system", "content": "You are a curriculum designer. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        response = await self._llm.generate(messages)
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            return Syllabus(
                repo_id=repo_id,
                persona=persona_id,
                title=data.get("title", f"Course: {repo.github_name}"),
                description=data.get("description", "AI Generated Course"),
                modules=[
                    Module(
                        title=m.get("title") or "Module",
                        description=m.get("description") or "",
                        lessons=[Lesson(**lesson_data) for lesson_data in m.get("lessons", [])],
                    )
                    for m in data.get("modules", [])
                ],
            )
        except Exception as exc:
            logger.error("Failed to generate curriculum V1: %s", exc)
            return Syllabus(
                repo_id=repo_id,
                persona=persona_id,
                title="Generation Failed",
                description="Could not generate curriculum. Please try again.",
                modules=[],
            )

    async def _generate_curriculum_v2(
        self,
        repo_id: str,
        persona_id: str,
        force_regenerate: bool = False,
        include_quality_meta: bool = False,
    ) -> Syllabus:
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        persona_id = self._normalize_persona(persona_id)
        persona = next((p for p in self.get_personas() if p.id == persona_id), self.get_personas()[0])
        blueprint = self.PERSONA_BLUEPRINTS[persona_id]
        now = datetime.now(timezone.utc)
        ttl = timedelta(days=max(1, int(settings.learning_cache_ttl_days)))

        cached = (
            self._db.query(LearningSyllabus)
            .filter(
                LearningSyllabus.repository_id == repo_id,
                LearningSyllabus.persona == persona_id,
            )
            .order_by(LearningSyllabus.created_at.desc())
            .first()
        )
        if (
            cached
            and not force_regenerate
            and (cached.expires_at is None or cached.expires_at > now.replace(tzinfo=None))
        ):
            payload = cached.syllabus_json or {}
            syllabus = self._syllabus_from_payload(repo_id, persona_id, payload)
            syllabus.cache_info = CacheInfo(
                source="cache",
                generated_at=cached.created_at.replace(tzinfo=timezone.utc).isoformat() if cached.created_at else None,
                expires_at=cached.expires_at.replace(tzinfo=timezone.utc).isoformat() if cached.expires_at else None,
                prompt_version=str(payload.get("prompt_version") or settings.learning_prompt_version),
                cache_hit=True,
            )
            if include_quality_meta:
                syllabus.quality_meta = payload.get("quality_meta")
            else:
                syllabus.quality_meta = None
            return syllabus

        retrieval_query = f"{blueprint['retrieval_query']} architecture file map"
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(retrieval_query),
            limit=24,
        )
        snippets: List[str] = []
        for doc in context_docs[:24]:
            file_path = doc.metadata.get("file_path", "unknown")
            snippets.append(f"File: {file_path}\n{doc.content[:900]}")
        context_str = "\n\n---\n\n".join(snippets)

        prompt = f"""
You are designing a 4-module codebase learning track.
Persona: {persona.name}
Persona Mission: {blueprint["mission"]}
Persona Tone: {blueprint["tone"]}
Required Topic Pillars: {", ".join(blueprint["pillars"])}
Repository: {repo.github_owner}/{repo.github_name}

Requirements:
- Exactly 4 modules.
- Each module has 2 to 4 lessons.
- Every lesson id must be lowercase kebab-case and unique across all modules.
- Every module and lesson must be concrete to this repository.
- Keep lesson types to: concept, code_tour, quiz.

Context:
{context_str}

Return valid JSON only:
{{
  "title": "Track title",
  "description": "Track description",
  "modules": [
    {{
      "title": "Module title",
      "description": "Module description",
      "lessons": [
        {{
          "id": "example-lesson-id",
          "title": "Lesson title",
          "description": "One sentence",
          "type": "concept",
          "estimated_minutes": 10
        }}
      ]
    }}
  ]
}}
"""
        raw = await self._llm.generate(
            [
                {"role": "system", "content": "You are a curriculum designer. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ]
        )

        fallback_used = False
        fallback_reason: Optional[str] = None
        lesson_id_seen: Set[str] = set()
        modules: List[Module] = []
        quality = {"persona_term_hits": 0, "persona_term_score": 0.0, "validation_errors": []}
        try:
            payload = json.loads(self._repair_json_like(self._extract_json_block(raw)))
            modules_payload = payload.get("modules", [])
            for m_idx, raw_module in enumerate(modules_payload[:4], start=1):
                raw_lessons = raw_module.get("lessons", [])[:4]
                if len(raw_lessons) < 2:
                    quality["validation_errors"].append(f"module_{m_idx}_too_few_lessons")
                    continue
                lessons: List[Lesson] = []
                for l_idx, raw_lesson in enumerate(raw_lessons, start=1):
                    lesson_title = (raw_lesson.get("title") or f"Lesson {m_idx}.{l_idx}").strip()
                    raw_id = (raw_lesson.get("id") or self._slugify(lesson_title)).strip().lower()
                    lesson_id = self._slugify(raw_id)
                    if not lesson_id or lesson_id in lesson_id_seen:
                        lesson_id = self._slugify(f"{persona_id}-{m_idx}-{l_idx}-{lesson_title}")
                    lesson_id_seen.add(lesson_id)
                    lesson_type = raw_lesson.get("type") or "concept"
                    if lesson_type not in {"concept", "code_tour", "quiz"}:
                        lesson_type = "concept"
                    estimated_minutes = int(raw_lesson.get("estimated_minutes") or 12)
                    estimated_minutes = max(5, min(40, estimated_minutes))
                    lessons.append(
                        Lesson(
                            id=lesson_id,
                            title=lesson_title,
                            description=(raw_lesson.get("description") or "Understand this area of the codebase.").strip(),
                            type=lesson_type,
                            estimated_minutes=estimated_minutes,
                        )
                    )
                modules.append(
                    Module(
                        title=(raw_module.get("title") or f"Module {m_idx}").strip(),
                        description=(raw_module.get("description") or "").strip(),
                        lessons=lessons[:4],
                    )
                )

            if len(modules) != 4:
                quality["validation_errors"].append("invalid_module_count")
                raise ValueError("invalid module count")

            joined = " ".join(
                [payload.get("title", ""), payload.get("description", "")]
                + [m.title + " " + m.description for m in modules]
                + [lesson.title + " " + lesson.description for m in modules for lesson in m.lessons]
            ).lower()
            hits = sum(1 for term in blueprint["relevance_terms"] if term in joined)
            quality["persona_term_hits"] = hits
            quality["persona_term_score"] = round(hits / max(1, len(blueprint["relevance_terms"])), 2)
            if hits < 2:
                quality["validation_errors"].append("weak_persona_relevance")
                raise ValueError("weak persona relevance")

            syllabus = Syllabus(
                repo_id=repo_id,
                persona=persona_id,
                title=(payload.get("title") or f"{persona.name} Track for {repo.github_name}").strip(),
                description=(payload.get("description") or "Persona-specific learning track").strip(),
                modules=modules,
            )
        except Exception as exc:
            fallback_used = True
            fallback_reason = str(exc)
            syllabus = self._fallback_curriculum(repo_id, repo.github_name, persona_id, blueprint)

        quality_meta = {
            "mode": "v2",
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "persona_term_hits": quality["persona_term_hits"],
            "persona_term_score": quality["persona_term_score"],
            "validation_errors": quality["validation_errors"],
        }
        expires_at = now + ttl
        syllabus.cache_info = CacheInfo(
            source="generated",
            generated_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            prompt_version=settings.learning_prompt_version,
            cache_hit=False,
        )
        if include_quality_meta:
            syllabus.quality_meta = quality_meta

        cache_payload = syllabus.model_dump()
        cache_payload["quality_meta"] = quality_meta
        cache_payload["prompt_version"] = settings.learning_prompt_version
        self._db.query(LearningSyllabus).filter(
            LearningSyllabus.repository_id == repo_id,
            LearningSyllabus.persona == persona_id,
        ).delete(synchronize_session=False)
        self._db.add(
            LearningSyllabus(
                repository_id=repo_id,
                persona=persona_id,
                syllabus_json=cache_payload,
                created_at=now.replace(tzinfo=None),
                expires_at=expires_at.replace(tzinfo=None),
            )
        )
        self._db.commit()
        logger.info(
            "learning_v2 curriculum generated repo=%s persona=%s fallback=%s",
            repo_id,
            persona_id,
            fallback_used,
        )
        return syllabus

    async def generate_lesson(
        self,
        repo_id: str,
        lesson_id: str,
        lesson_title: str,
        persona_id: Optional[str] = None,
        module_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> Optional[LessonContent]:
        """Generate detailed content for a specific lesson."""
        if not settings.learning_v2_enabled:
            return await self._generate_lesson_v1(repo_id, lesson_id, lesson_title)

        try:
            return await self._generate_lesson_v2(
                repo_id=repo_id,
                lesson_id=lesson_id,
                lesson_title=lesson_title,
                persona_id=persona_id,
                module_id=module_id,
                force_regenerate=force_regenerate,
            )
        except Exception as exc:
            logger.error("Learning V2 lesson failed, falling back to V1: %s", exc)
            return await self._generate_lesson_v1(repo_id, lesson_id, lesson_title)

    async def get_or_generate_lesson(
        self,
        repo_id: str,
        lesson_id: str,
        persona_id: str,
        module_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> Optional[LessonContent]:
        title = self._resolve_lesson_title(repo_id, lesson_id, persona_id) or f"Lesson {lesson_id}"
        return await self.generate_lesson(
            repo_id=repo_id,
            lesson_id=lesson_id,
            lesson_title=title,
            persona_id=persona_id,
            module_id=module_id,
            force_regenerate=force_regenerate,
        )

    async def _generate_lesson_v1(self, repo_id: str, lesson_id: str, lesson_title: str) -> Optional[LessonContent]:
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(lesson_title),
            limit=15,
        )

        available_files = set()
        for d in context_docs:
            file_path = d.metadata.get("file_path")
            if file_path and Path(file_path).suffix.lower() in self.LESSON_CODE_EXTENSIONS:
                available_files.add(file_path)

        files_list = "\n".join(sorted(available_files)) if available_files else "No code files indexed."
        context_str = "\n\n---\n\n".join(
            [f"File: {d.metadata.get('file_path', 'unknown')}\n{d.content[:2000]}" for d in context_docs]
        )

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
- If you provide diagram_mermaid, it must be meaningful (minimum 5 nodes) and use real component/file names.
- Never use placeholder nodes like A, B, C.

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
  "diagram_mermaid": "Optional Mermaid flowchart with real node labels and real relationships from this codebase"
}}
"""
        messages = [
            {"role": "system", "content": "You are a coding instructor. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.generate(messages)

        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            filtered_refs = self._normalize_code_references(
                data.get("code_references", []),
                self._load_file_line_map(repo_id),
                available_files=available_files,
            )
            diagram_mermaid, _diagram_source = self._select_high_quality_mermaid(
                raw_code=data.get("diagram_mermaid"),
                lesson_title=lesson_title,
                persona_id="new_hire",
                module_id=None,
                references=filtered_refs,
                available_files=available_files,
            )
            return LessonContent(
                id=lesson_id,
                title=lesson_title,
                content_markdown=data.get("content_markdown", "No content generated."),
                code_references=filtered_refs,
                diagram_mermaid=diagram_mermaid,
            )
        except Exception as exc:
            logger.error("Failed to generate lesson V1: %s", exc)
            return None

    async def _generate_lesson_v2(
        self,
        repo_id: str,
        lesson_id: str,
        lesson_title: str,
        persona_id: Optional[str] = None,
        module_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> Optional[LessonContent]:
        persona_id = self._normalize_persona(persona_id or "new_hire")
        blueprint = self.PERSONA_BLUEPRINTS[persona_id]
        now = datetime.now(timezone.utc)
        ttl = timedelta(days=max(1, int(settings.learning_cache_ttl_days)))
        line_map = self._load_file_line_map(repo_id)

        cache_query = (
            self._db.query(LearningLesson)
            .filter(
                LearningLesson.repository_id == repo_id,
                LearningLesson.lesson_id == lesson_id,
                LearningLesson.persona == persona_id,
            )
            .order_by(LearningLesson.created_at.desc())
        )
        if module_id:
            cache_query = cache_query.filter(LearningLesson.module_id == module_id)
        cached = cache_query.first()
        if (
            cached
            and not force_regenerate
            and (cached.expires_at is None or cached.expires_at > now.replace(tzinfo=None))
        ):
            payload = cached.lesson_json or {}
            content = self._lesson_from_payload(repo_id, lesson_id, lesson_title, persona_id, module_id, payload)
            content.cache_info = CacheInfo(
                source="cache",
                generated_at=cached.created_at.replace(tzinfo=timezone.utc).isoformat() if cached.created_at else None,
                expires_at=cached.expires_at.replace(tzinfo=timezone.utc).isoformat() if cached.expires_at else None,
                prompt_version=cached.prompt_version or settings.learning_prompt_version,
                cache_hit=True,
            )
            return content

        query = f"{lesson_title} {' '.join(blueprint['pillars'])} {blueprint['retrieval_query']}"
        context_docs = await self._vector_store.search(
            collection_name=repo_id,
            query_embedding=await self._vector_store._embedding_service.embed_query(query),
            limit=20,
        )
        available_files: Set[str] = set()
        context_parts: List[str] = []
        for doc in context_docs:
            file_path = doc.metadata.get("file_path")
            if file_path and Path(file_path).suffix.lower() in self.LESSON_CODE_EXTENSIONS:
                available_files.add(file_path)
            context_parts.append(f"File: {file_path or 'unknown'}\n{doc.content[:1500]}")

        prompt = f"""
You are an expert technical instructor producing a persona-specific lesson.
Lesson Title: {lesson_title}
Persona: {persona_id}
Mission: {blueprint["mission"]}
Tone: {blueprint["tone"]}
Required Pillars: {", ".join(blueprint["pillars"])}
Module Context: {module_id or "general"}

Output requirements:
- Markdown MUST contain these exact section headings:
  1) Mission Brief
  2) Objectives
  3) Architecture Walkthrough
  4) Code Deep Dive
  5) Pitfalls
  6) Recap
- Minimum 550 words.
- Explain concrete files and rationale.
- No code fences inside content_markdown.
- diagram_mermaid must be a real architecture diagram with minimum 5 nodes and real labels.
- NEVER output placeholder nodes (A, B, C) or generic toy graphs.

Code files (valid for references only):
{chr(10).join(sorted(available_files)) if available_files else "No code files indexed"}

Repository context:
{chr(10).join(context_parts)}

Return strict JSON:
{{
  "content_markdown": "markdown string",
  "code_references": [
    {{"file_path":"...", "start_line":1, "end_line":20, "description":"..."}}
  ],
  "diagram_mermaid": "Mermaid flowchart using actual component/file names from this codebase"
}}
"""
        raw = await self._llm.generate(
            [
                {"role": "system", "content": "You are a coding instructor. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ]
        )

        fallback_used = False
        fallback_reason: Optional[str] = None
        quality: Dict[str, Any] = {
            "mode": "v2",
            "section_score": 0.0,
            "persona_term_score": 0.0,
            "reference_count": 0,
            "fallback_used": False,
            "fallback_reason": None,
        }

        try:
            payload = json.loads(self._repair_json_like(self._extract_json_block(raw)))
            content_markdown = str(payload.get("content_markdown") or "").strip()
            references = self._normalize_code_references(
                payload.get("code_references", []),
                line_map,
                available_files=available_files,
            )
            diagram_mermaid, diagram_source = self._select_high_quality_mermaid(
                raw_code=payload.get("diagram_mermaid"),
                lesson_title=lesson_title,
                persona_id=persona_id,
                module_id=module_id,
                references=references,
                available_files=available_files,
            )
            section_hits = self._score_lesson_sections(content_markdown)
            quality["section_score"] = round(section_hits / len(self.REQUIRED_LESSON_SECTIONS), 2)

            lowered = content_markdown.lower()
            term_hits = sum(1 for term in blueprint["relevance_terms"] if term in lowered)
            quality["persona_term_score"] = round(term_hits / max(1, len(blueprint["relevance_terms"])), 2)
            quality["reference_count"] = len(references)
            quality["diagram_quality"] = diagram_source
            if quality["section_score"] < 0.66:
                raise ValueError("missing required lesson sections")
            if quality["persona_term_score"] < 0.2:
                raise ValueError("weak persona relevance")
            if available_files and len(references) < 1:
                raise ValueError("no valid references")

            lesson = LessonContent(
                id=lesson_id,
                title=lesson_title,
                content_markdown=content_markdown,
                code_references=references,
                diagram_mermaid=diagram_mermaid,
                persona=persona_id,
                module_id=module_id,
                quality_meta=quality,
            )
        except Exception as exc:
            fallback_used = True
            fallback_reason = str(exc)
            fallback_refs = self._normalize_code_references(
                [
                    {
                        "file_path": file_path,
                        "start_line": 1,
                        "end_line": min(40, line_map.get(file_path, 40)),
                        "description": "Start here to map this lesson to concrete implementation details.",
                    }
                    for file_path in sorted(available_files)[:3]
                ],
                line_map,
                available_files=available_files,
            )
            quality["fallback_used"] = True
            quality["fallback_reason"] = fallback_reason
            quality["reference_count"] = len(fallback_refs)
            quality["diagram_quality"] = "fallback"
            lesson = LessonContent(
                id=lesson_id,
                title=lesson_title,
                content_markdown=self._build_lesson_fallback_markdown(lesson_title, persona_id, module_id, blueprint),
                code_references=fallback_refs,
                diagram_mermaid=self._build_fallback_mermaid(
                    lesson_title=lesson_title,
                    persona_id=persona_id,
                    module_id=module_id,
                    references=fallback_refs,
                    available_files=available_files,
                ),
                persona=persona_id,
                module_id=module_id,
                quality_meta=quality,
            )

        expires_at = now + ttl
        lesson.cache_info = CacheInfo(
            source="generated",
            generated_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            prompt_version=settings.learning_prompt_version,
            cache_hit=False,
        )
        cache_payload = lesson.model_dump()
        cache_payload["prompt_version"] = settings.learning_prompt_version

        stale_query = self._db.query(LearningLesson).filter(
            LearningLesson.repository_id == repo_id,
            LearningLesson.lesson_id == lesson_id,
            LearningLesson.persona == persona_id,
        )
        if module_id:
            stale_query = stale_query.filter(LearningLesson.module_id == module_id)
        stale_query.delete(synchronize_session=False)
        self._db.add(
            LearningLesson(
                repository_id=repo_id,
                persona=persona_id,
                lesson_id=lesson_id,
                module_id=module_id,
                lesson_json=cache_payload,
                quality_meta=quality,
                prompt_version=settings.learning_prompt_version,
                created_at=now.replace(tzinfo=None),
                expires_at=expires_at.replace(tzinfo=None),
            )
        )
        self._db.commit()
        logger.info(
            "learning_v2 lesson generated repo=%s persona=%s lesson=%s fallback=%s",
            repo_id,
            persona_id,
            lesson_id,
            fallback_used,
        )
        return lesson

    def _normalize_persona(self, persona_id: str) -> str:
        candidate = (persona_id or "new_hire").strip().lower()
        if candidate not in self.PERSONA_BLUEPRINTS:
            return "new_hire"
        return candidate

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
        normalized = re.sub(r"-{2,}", "-", normalized)
        return normalized[:90] or "lesson"

    def _fallback_curriculum(
        self,
        repo_id: str,
        repo_name: str,
        persona_id: str,
        blueprint: Dict[str, Any],
    ) -> Syllabus:
        modules: List[Module] = []
        for idx, pillar in enumerate(blueprint["pillars"][:4], start=1):
            lesson_one = Lesson(
                id=self._slugify(f"{persona_id}-m{idx}-foundations"),
                title=f"{pillar.title()} Foundations",
                description=f"Build working knowledge of {pillar} in this repository.",
                type="concept",
                estimated_minutes=12,
            )
            lesson_two = Lesson(
                id=self._slugify(f"{persona_id}-m{idx}-walkthrough"),
                title=f"{pillar.title()} Code Walkthrough",
                description=f"Trace the core files that implement {pillar}.",
                type="code_tour",
                estimated_minutes=15,
            )
            modules.append(
                Module(
                    title=f"Module {idx}: {pillar.title()}",
                    description=f"Persona-focused mastery of {pillar}.",
                    lessons=[lesson_one, lesson_two],
                )
            )
        return Syllabus(
            repo_id=repo_id,
            persona=persona_id,
            title=f"{persona_id.replace('_', ' ').title()} Track for {repo_name}",
            description=blueprint["mission"],
            modules=modules,
        )

    def _syllabus_from_payload(self, repo_id: str, persona_id: str, payload: Dict[str, Any]) -> Syllabus:
        modules: List[Module] = []
        for raw_module in payload.get("modules", []):
            lessons: List[Lesson] = []
            for raw_lesson in raw_module.get("lessons", []):
                try:
                    lessons.append(
                        Lesson(
                            id=self._slugify(str(raw_lesson.get("id") or raw_lesson.get("title") or "lesson")),
                            title=str(raw_lesson.get("title") or "Lesson"),
                            description=str(raw_lesson.get("description") or ""),
                            type=(raw_lesson.get("type") or "concept"),
                            estimated_minutes=max(5, int(raw_lesson.get("estimated_minutes") or 10)),
                        )
                    )
                except Exception:
                    continue
            modules.append(
                Module(
                    title=str(raw_module.get("title") or "Module"),
                    description=str(raw_module.get("description") or ""),
                    lessons=lessons,
                )
            )
        return Syllabus(
            repo_id=repo_id,
            persona=persona_id,
            title=str(payload.get("title") or "Learning Track"),
            description=str(payload.get("description") or ""),
            modules=modules,
            quality_meta=payload.get("quality_meta"),
        )

    def _resolve_lesson_title(self, repo_id: str, lesson_id: str, persona_id: Optional[str] = None) -> Optional[str]:
        persona_id = self._normalize_persona(persona_id or "new_hire")
        query = self._db.query(LearningSyllabus).filter(LearningSyllabus.repository_id == repo_id)
        if persona_id:
            persona_first = query.filter(LearningSyllabus.persona == persona_id).order_by(LearningSyllabus.created_at.desc()).first()
            if persona_first:
                title = self._lesson_title_from_syllabus_payload(persona_first.syllabus_json, lesson_id)
                if title:
                    return title

        for syllabus in query.order_by(LearningSyllabus.created_at.desc()).all():
            title = self._lesson_title_from_syllabus_payload(syllabus.syllabus_json, lesson_id)
            if title:
                return title
        return None

    def _lesson_title_from_syllabus_payload(self, payload: Dict[str, Any], lesson_id: str) -> Optional[str]:
        for module in (payload or {}).get("modules", []):
            for lesson in module.get("lessons", []):
                if lesson.get("id") == lesson_id:
                    return lesson.get("title")
        return None

    def _load_file_line_map(self, repo_id: str) -> Dict[str, int]:
        rows = self._db.query(CodeFile.path, CodeFile.line_count).filter(CodeFile.repository_id == repo_id).all()
        return {path: int(line_count or 1) for path, line_count in rows if path}

    def _normalize_code_references(
        self,
        references: List[Dict[str, Any]],
        file_line_map: Dict[str, int],
        available_files: Optional[Set[str]] = None,
    ) -> List[CodeReference]:
        normalized: List[CodeReference] = []
        allowed_files = set(available_files or set())

        for raw in references or []:
            file_path = str(raw.get("file_path") or "").strip()
            if not file_path:
                continue
            if allowed_files and file_path not in allowed_files:
                continue
            if Path(file_path).suffix.lower() not in self.LESSON_CODE_EXTENSIONS:
                continue
            if file_path not in file_line_map:
                continue

            max_line = max(1, int(file_line_map.get(file_path, 1)))
            start = max(1, int(raw.get("start_line") or 1))
            end = max(start, int(raw.get("end_line") or start))
            if start > max_line:
                continue
            end = min(end, max_line)

            normalized.append(
                CodeReference(
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    description=str(raw.get("description") or "Relevant implementation details for this lesson."),
                )
            )

        # Keep deterministic order and avoid duplicate windows.
        dedup: Dict[str, CodeReference] = {}
        for item in normalized:
            key = f"{item.file_path}:{item.start_line}:{item.end_line}"
            if key not in dedup:
                dedup[key] = item
        return list(dedup.values())[:8]

    def _score_lesson_sections(self, markdown: str) -> int:
        lowered = (markdown or "").lower()
        return sum(1 for heading in self.REQUIRED_LESSON_SECTIONS if heading in lowered)

    def _is_placeholder_mermaid(self, code: Optional[str]) -> bool:
        text = (code or "").strip()
        if not text:
            return True
        lowered = text.lower()
        if not any(keyword in lowered for keyword in ("graph", "flowchart", "sequencediagram", "classdiagram", "statediagram")):
            return True
        if re.search(r"\b[aA]\s*-->", text):
            # Very common toy output from LLMs.
            return True
        edges = re.findall(r"-->|---|==>", text)
        if len(edges) < 3:
            return True
        raw_labels = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\[(.*?)\]", text)
        labels = [label.strip().strip('"').strip("'") for label in raw_labels if label.strip()]
        if labels:
            meaningful = [label for label in labels if len(label.strip()) > 2]
            if len(meaningful) < 4:
                return True
            # If labels are all single tokens like A/B/C it's low-value.
            short_tokens = [label for label in meaningful if re.fullmatch(r"[A-Za-z]{1,2}\d*", label.strip())]
            if short_tokens and len(short_tokens) >= int(len(meaningful) * 0.6):
                return True
            generic_terms = {
                "node",
                "component",
                "service",
                "module",
                "system",
                "process",
                "step",
                "input",
                "output",
                "start",
                "end",
            }
            normalized_labels = [
                re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
                for label in meaningful
            ]
            generic_count = sum(
                1
                for label in normalized_labels
                if label in generic_terms or re.fullmatch(r"[a-z]\d*", label)
            )
            if generic_count and generic_count >= int(len(normalized_labels) * 0.6):
                return True
        else:
            # No quoted labels usually means IDs only; treat as low quality for lesson diagrams.
            ids = re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\b(?=\s*-->)", text)
            if ids and all(len(node_id) <= 2 for node_id in set(ids)):
                return True
        return False

    def _mermaid_mentions_repository_context(
        self,
        code: str,
        references: List[CodeReference],
        available_files: Optional[Set[str]] = None,
    ) -> bool:
        lowered = (code or "").lower()
        if not lowered:
            return False

        files = [ref.file_path for ref in references if ref.file_path]
        if not files and available_files:
            files = sorted(list(available_files))[:6]
        if not files:
            # Without file context, keep placeholder checks only.
            return True

        tokens: Set[str] = set()
        for file_path in files[:8]:
            path = Path(file_path)
            parts = [path.name, path.stem, path.parent.name]
            for part in parts:
                part = (part or "").lower().strip()
                if part and len(part) >= 3:
                    tokens.add(part)

        if not tokens:
            return True
        hits = sum(1 for token in tokens if token in lowered)
        threshold = 2 if len(tokens) >= 4 else 1
        return hits >= threshold

    def _escape_mermaid_label(self, text: str) -> str:
        return (text or "").replace('"', "'").replace("[", "(").replace("]", ")")

    def _short_file_label(self, file_path: str) -> str:
        path = Path(file_path)
        parent = path.parent.name
        name = path.name
        if parent and parent != ".":
            return f"{parent}/{name}"
        return name

    def _build_fallback_mermaid(
        self,
        lesson_title: str,
        persona_id: str,
        module_id: Optional[str],
        references: List[CodeReference],
        available_files: Optional[Set[str]] = None,
    ) -> str:
        files: List[str] = []
        for ref in references:
            if ref.file_path and ref.file_path not in files:
                files.append(ref.file_path)
        if not files and available_files:
            files = sorted(list(available_files))[:4]
        files = files[:4]

        def classify(path: str) -> str:
            lowered = path.lower()
            if any(token in lowered for token in ("/app/", "/pages/", "/components/", "/ui/", "main.ts", "main.tsx", "index.tsx")):
                return "entry"
            if any(token in lowered for token in ("/routes/", "/api/", "/controllers/", "/handlers/", "/services/")):
                return "orchestration"
            if any(token in lowered for token in ("/core/", "/domain/", "/engine/", "/lib/", "/workflow/", "/logic/")):
                return "core"
            if any(token in lowered for token in ("/db/", "/model", "/store/", "/repository/", "/schema", "/migration")):
                return "data"
            return "support"

        buckets: Dict[str, List[str]] = {"entry": [], "orchestration": [], "core": [], "data": [], "support": []}
        for file_path in files:
            buckets[classify(file_path)].append(file_path)

        def choose_label(bucket: str, fallback: str) -> str:
            if buckets[bucket]:
                return self._escape_mermaid_label(self._short_file_label(buckets[bucket][0]))
            return fallback

        entry_label = choose_label("entry", "UI / Entry Surface")
        orchestration_label = choose_label("orchestration", "API / Service Orchestration")
        core_label = choose_label("core", "Core Business Logic")
        data_label = choose_label("data", "Data / State Layer")

        persona_label = persona_id.replace("_", " ").title()
        title_label = self._escape_mermaid_label(lesson_title)
        module_label = self._escape_mermaid_label(module_id or "General module")
        if files:
            file_rows = [self._escape_mermaid_label(self._short_file_label(path)) for path in files]
            files_label = "<br/>".join(file_rows)
        else:
            files_label = "Entry points and routing<br/>Core processing path<br/>Persistence boundaries"

        lines = [
            "flowchart TB",
            f'  GOAL["Lesson Goal: {title_label}"]',
            f'  PERSONA["Persona Lens: {persona_label}"]',
            f'  MODULE["Module Focus: {module_label}"]',
            f'  FILES["Referenced Code Files:<br/>{files_label}"]',
            "  GOAL --> PERSONA",
            "  PERSONA --> MODULE",
            '  subgraph EXEC["Repository Execution Flow"]',
            "    direction TB",
            f'    ENTRY["Entry: {entry_label}"]',
            f'    ORCH["Orchestration: {orchestration_label}"]',
            f'    CORE["Core Logic: {core_label}"]',
            f'    DATA["Data Layer: {data_label}"]',
            '    RESULT["Practical Outcome"]',
            "    ENTRY --> ORCH",
            "    ORCH --> CORE",
            "    CORE --> DATA",
            "    DATA --> RESULT",
            "  end",
            "  MODULE --> ENTRY",
            "  MODULE -.evidence.-> FILES",
            "  FILES -.context.-> ORCH",
        ]
        return "\n".join(lines)

    def _select_high_quality_mermaid(
        self,
        raw_code: Optional[str],
        lesson_title: str,
        persona_id: str,
        module_id: Optional[str],
        references: List[CodeReference],
        available_files: Optional[Set[str]] = None,
    ) -> Tuple[str, str]:
        raw = str(raw_code or "").strip()
        if self._is_placeholder_mermaid(raw):
            return (
                self._build_fallback_mermaid(
                    lesson_title=lesson_title,
                    persona_id=persona_id,
                    module_id=module_id,
                    references=references,
                    available_files=available_files,
                ),
                "fallback",
            )
        if not self._mermaid_mentions_repository_context(raw, references, available_files):
            return (
                self._build_fallback_mermaid(
                    lesson_title=lesson_title,
                    persona_id=persona_id,
                    module_id=module_id,
                    references=references,
                    available_files=available_files,
                ),
                "fallback",
            )
        return raw, "llm"

    def _build_lesson_fallback_markdown(
        self,
        lesson_title: str,
        persona_id: str,
        module_id: Optional[str],
        blueprint: Dict[str, Any],
    ) -> str:
        return f"""## Mission Brief
This lesson is tuned for the **{persona_id.replace('_', ' ')}** track. Your mission is to understand how **{lesson_title}** fits the real architecture and where to act safely.

## Objectives
- Map the main components involved in {lesson_title}
- Identify repository-specific conventions and assumptions
- Locate risk points and integration touchpoints

## Architecture Walkthrough
Start by tracing the primary execution path for this topic. Focus on boundary layers, data shape transitions, and where behavior branches.

## Code Deep Dive
Use the file references in this lesson to inspect entrypoints, orchestration logic, and lower-level helpers. Read each file with intent: what contract it serves, what dependencies it has, and what assumptions it encodes.

## Pitfalls
- Confusing transport-level behavior with domain-level behavior
- Changing contracts without validating downstream impact
- Ignoring implicit assumptions embedded in helper utilities

## Recap
You now have a practical map for **{lesson_title}** in the repository. Continue with {module_id or "the next module"} to deepen system mastery.

Track pillars: {", ".join(blueprint.get("pillars", []))}.
"""

    def _lesson_from_payload(
        self,
        repo_id: str,
        lesson_id: str,
        lesson_title: str,
        persona_id: str,
        module_id: Optional[str],
        payload: Dict[str, Any],
    ) -> LessonContent:
        line_map = self._load_file_line_map(repo_id)
        refs = self._normalize_code_references(payload.get("code_references", []), line_map)
        if not refs:
            refs = []
            for raw_ref in payload.get("code_references", [])[:6]:
                try:
                    if not raw_ref.get("file_path"):
                        continue
                    refs.append(
                        CodeReference(
                            file_path=str(raw_ref["file_path"]),
                            start_line=max(1, int(raw_ref.get("start_line") or 1)),
                            end_line=max(1, int(raw_ref.get("end_line") or raw_ref.get("start_line") or 1)),
                            description=str(raw_ref.get("description") or "Relevant implementation details."),
                        )
                    )
                except Exception:
                    continue
        available_files = {ref.file_path for ref in refs if ref.file_path}
        diagram_mermaid, _diagram_source = self._select_high_quality_mermaid(
            raw_code=payload.get("diagram_mermaid"),
            lesson_title=str(payload.get("title") or lesson_title),
            persona_id=(payload.get("persona") or persona_id),
            module_id=(payload.get("module_id") or module_id),
            references=refs,
            available_files=available_files,
        )
        return LessonContent(
            id=lesson_id,
            title=str(payload.get("title") or lesson_title),
            content_markdown=str(payload.get("content_markdown") or "No content generated."),
            code_references=refs,
            diagram_mermaid=diagram_mermaid,
            persona=payload.get("persona") or persona_id,
            module_id=payload.get("module_id") or module_id,
            quality_meta=payload.get("quality_meta"),
        )

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

    GRAPH_CODE_EXTENSIONS = {
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts",
        ".py", ".go", ".java", ".rs", ".rb", ".php",
    }
    GRAPH_IMPORT_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs", ".py", ".json"]
    IMPORT_PATTERNS = [
        r'import\s+(?:type\s+)?(?:[^;]*?\s+from\s+)?["\']([^"\']+)["\']',
        r'require\s*\(\s*["\']([^"\']+)["\']\s*\)',
        r'import\s*\(\s*["\']([^"\']+)["\']\s*\)',
        r'export\s+\*\s+from\s+["\']([^"\']+)["\']',
        r'export\s+\{[^}]*\}\s+from\s+["\']([^"\']+)["\']',
        r'^from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',
        r'^import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',
    ]

    async def generate_graph(
        self,
        repo_id: str,
        granularity: str = "file",
        scope: Optional[str] = None,
        focus_node: Optional[str] = None,
        hops: int = 1,
    ) -> Optional[object]:
        """Generate deterministic dependency graph with adaptive dense-graph controls."""
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found for graph generation")
            return None

        granularity = (granularity or "file").strip().lower()
        if granularity not in {"auto", "module", "file"}:
            granularity = "file"
        hops = max(1, min(2, int(hops or 1)))
        scope = (scope or "").strip() or None
        focus_node = (focus_node or "").strip() or None

        files = self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
        if not files:
            empty_stats = GraphStats(nodes=0, edges=0, clusters=0, density=0.0)
            meta = GraphMeta(
                generated_at=datetime.now(timezone.utc).isoformat(),
                source="deterministic",
                truncated=False,
                stats=empty_stats,
                view="file",
                scope=scope,
                recommended_entry="file",
                entry_reason="no_files",
                raw_stats=empty_stats,
                cross_module_ratio=0.0,
                internal_edges_summarized=0,
                edge_budget={"per_node": 0, "max_edges": 0},
            )
            return DependencyGraph(nodes=[], edges=[], meta=meta)

        repo_version = (
            repo.updated_at.isoformat()
            if getattr(repo, "updated_at", None)
            else repo.last_indexed_at.isoformat() if getattr(repo, "last_indexed_at", None) else "na"
        )
        cache_key = self._build_graph_cache_key(repo_id, granularity, scope, focus_node, hops, repo_version)
        cached_graph = self._get_cached_graph(cache_key)
        if cached_graph is not None:
            return cached_graph

        file_map = {f.path: f for f in files if f.path}
        all_paths = set(file_map.keys())
        code_paths = [
            path for path, code_file in file_map.items()
            if Path(path).suffix.lower() in self.GRAPH_CODE_EXTENSIONS and (code_file.line_count or 0) > 0
        ]
        if not code_paths:
            code_paths = sorted(all_paths)

        # Deterministic file-level baseline from repository inventory.
        file_nodes_by_id: Dict[str, GraphNode] = {
            path: self._build_graph_node_from_file(path, file_map[path]) for path in sorted(code_paths)
        }
        file_edges = self._build_deterministic_edges(repo, sorted(code_paths), all_paths, file_map)

        for edge in file_edges:
            if edge.source in file_map and edge.source not in file_nodes_by_id:
                file_nodes_by_id[edge.source] = self._build_graph_node_from_file(edge.source, file_map[edge.source])
            if edge.target in file_map and edge.target not in file_nodes_by_id:
                file_nodes_by_id[edge.target] = self._build_graph_node_from_file(edge.target, file_map[edge.target])

        file_nodes = list(file_nodes_by_id.values())
        file_nodes, file_edges = self._apply_node_metrics(file_nodes, file_edges)
        file_edges = self._rank_edges(file_nodes, file_edges)
        raw_stats = self._compute_graph_stats(file_nodes, file_edges)
        module_connectivity = self._summarize_module_connectivity(file_edges)

        dense_mode_enabled = bool(getattr(settings, "graph_dense_mode_v21", True))
        recommended_entry, auto_entry_reason = self._resolve_recommended_entry(
            raw_stats,
            module_connectivity["cross_ratio"],
            module_connectivity["cross_edges"],
        )
        resolved_view = "file"
        entry_reason = auto_entry_reason
        if granularity == "auto":
            resolved_view = recommended_entry if dense_mode_enabled else "file"
            if not dense_mode_enabled:
                entry_reason = "dense_mode_disabled"
        elif granularity in {"module", "file"}:
            resolved_view = granularity
            entry_reason = f"user_selected_{granularity}"
        else:
            resolved_view = "file"
            entry_reason = "invalid_granularity_fallback"

        working_nodes = file_nodes
        working_edges = file_edges
        resolved_scope = scope
        internal_edges_summarized = module_connectivity["internal_edges"]

        max_nodes = max(20, int(getattr(settings, "graph_v2_max_nodes", 160)))
        max_edges = max(25, int(getattr(settings, "graph_v2_max_edges", 600)))
        per_node_budget = max(4, int(getattr(settings, "graph_v21_edge_budget_file_per_node", 10)))

        if resolved_view == "module":
            working_nodes, working_edges = self._build_module_graph(file_nodes, file_edges)
            working_nodes, working_edges = self._apply_node_metrics(working_nodes, working_edges)
            working_edges = self._rank_edges(working_nodes, working_edges)
            max_nodes = max(12, int(getattr(settings, "graph_v21_module_max_nodes", 120)))
            max_edges = max(30, int(getattr(settings, "graph_v21_module_max_edges", 260)))
            per_node_budget = max(4, int(getattr(settings, "graph_v21_edge_budget_module_per_node", 14)))
            resolved_scope = None
        else:
            if resolved_scope:
                working_nodes, working_edges = self._extract_scoped_file_subgraph(
                    file_nodes,
                    file_edges,
                    resolved_scope,
                    hops=max(1, hops),
                )
                working_nodes, working_edges = self._apply_node_metrics(working_nodes, working_edges)
                working_edges = self._rank_edges(working_nodes, working_edges)
                max_nodes = max(20, int(getattr(settings, "graph_v21_scope_max_nodes", 220)))
                max_edges = max(40, int(getattr(settings, "graph_v21_scope_max_edges", 420)))

        if focus_node:
            working_nodes, working_edges = self._extract_focus_subgraph(
                working_nodes,
                working_edges,
                focus_node,
                hops=max(1, hops),
            )
            working_nodes, working_edges = self._apply_node_metrics(working_nodes, working_edges)
            working_edges = self._rank_edges(working_nodes, working_edges)

        truncated = False
        if len(working_nodes) > max_nodes:
            prune_filter_orphans = not settings.graph_include_orphans
            if resolved_view == "module":
                prune_filter_orphans = (
                    not settings.graph_include_orphans
                    and bool(getattr(settings, "graph_v22_module_filter_orphans", False))
                )
            working_nodes, working_edges = self._prune_graph(
                working_nodes,
                working_edges,
                max_nodes=max_nodes,
                filter_orphans=prune_filter_orphans,
            )
            working_edges = self._rank_edges(working_nodes, working_edges)
            truncated = True

        budgeted_edges = self._apply_per_node_edge_budget(working_nodes, working_edges, per_node_budget)
        if len(budgeted_edges) < len(working_edges):
            working_edges = budgeted_edges
            truncated = True

        if len(working_edges) > max_edges:
            working_edges = sorted(
                working_edges,
                key=lambda edge: (
                    -(edge.rank or 0.0),
                    -(edge.weight or 1),
                    -(edge.confidence or 0.0),
                    edge.source,
                    edge.target,
                    edge.relation or edge.type or "imports",
                ),
            )[:max_edges]
            truncated = True

        should_filter_orphans = not settings.graph_include_orphans
        if resolved_view == "module":
            should_filter_orphans = (
                not settings.graph_include_orphans
                and bool(getattr(settings, "graph_v22_module_filter_orphans", False))
            )

        if should_filter_orphans:
            working_nodes, working_edges = self._filter_connected_nodes(working_nodes, working_edges)

        source = "deterministic"
        if bool(getattr(settings, "graph_v2_enabled", True)) and resolved_view == "file":
            enrich_nodes = [node for node in working_nodes if (node.entity or "file") == "file"]
            if await self._maybe_enrich_nodes_with_llm(repo_id, enrich_nodes):
                source = "hybrid"

        working_nodes = sorted(working_nodes, key=lambda node: node.id)
        working_edges = sorted(
            working_edges,
            key=lambda edge: (
                edge.source,
                edge.target,
                edge.relation or edge.type or "imports",
                edge.label,
            ),
        )

        stats = self._compute_graph_stats(working_nodes, working_edges)
        meta = GraphMeta(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            truncated=truncated,
            stats=stats,
            view=resolved_view,
            scope=resolved_scope,
            recommended_entry=recommended_entry,
            entry_reason=entry_reason,
            raw_stats=raw_stats,
            cross_module_ratio=module_connectivity["cross_ratio"],
            internal_edges_summarized=internal_edges_summarized,
            edge_budget={
                "per_node": per_node_budget,
                "max_edges": max_edges,
                "hops": hops,
                "focus": bool(focus_node),
            },
        )
        result = DependencyGraph(nodes=working_nodes, edges=working_edges, meta=meta)
        self._set_cached_graph(cache_key, result)

        logger.info(
            "Generated graph v2.1 with %s nodes and %s edges (view=%s source=%s truncated=%s)",
            len(working_nodes),
            len(working_edges),
            resolved_view,
            source,
            truncated,
        )
        return result

    def _resolve_recommended_entry(
        self,
        raw_stats: GraphStats,
        cross_module_ratio: float,
        cross_module_edges: int,
    ) -> tuple[str, str]:
        auto_nodes = max(20, int(getattr(settings, "graph_v21_auto_nodes_threshold", 90)))
        auto_edges = max(40, int(getattr(settings, "graph_v21_auto_edges_threshold", 240)))
        dense = raw_stats.nodes > auto_nodes or raw_stats.edges > auto_edges
        if not dense:
            return "file", "below_dense_threshold"

        min_cross_ratio = float(getattr(settings, "graph_v22_min_cross_module_ratio_for_overview", 0.08))
        min_cross_edges = max(1, int(getattr(settings, "graph_v22_min_cross_module_edges_for_overview", 18)))
        if cross_module_ratio < min_cross_ratio or cross_module_edges < min_cross_edges:
            return "file", "low_cross_module_signal"
        return "module", "dense_with_cross_module_signal"

    def _recommended_entry_view(
        self,
        raw_stats: GraphStats,
        cross_module_ratio: float = 1.0,
        cross_module_edges: int = 999999,
    ) -> str:
        return self._resolve_recommended_entry(raw_stats, cross_module_ratio, cross_module_edges)[0]

    def _summarize_module_connectivity(self, edges: List[GraphEdge]) -> Dict[str, float]:
        if not edges:
            return {"cross_ratio": 0.0, "cross_edges": 0, "internal_edges": 0}

        cross_weight = 0
        internal_weight = 0
        cross_edges = 0
        for edge in edges:
            source_module = self._module_key_for_path(edge.source)
            target_module = self._module_key_for_path(edge.target)
            weight = max(1, edge.weight or 1)
            if source_module == target_module:
                internal_weight += weight
            else:
                cross_weight += weight
                cross_edges += 1

        total_weight = cross_weight + internal_weight
        ratio = round((cross_weight / total_weight), 4) if total_weight else 0.0
        return {
            "cross_ratio": ratio,
            "cross_edges": cross_edges,
            "internal_edges": int(internal_weight),
        }

    def _build_graph_cache_key(
        self,
        repo_id: str,
        granularity: str,
        scope: Optional[str],
        focus_node: Optional[str],
        hops: int,
        repo_version: str,
    ) -> str:
        return "|".join(
            [
                repo_id,
                granularity,
                scope or "",
                focus_node or "",
                str(hops),
                repo_version,
            ]
        )

    def _get_cached_graph(self, key: str) -> Optional[DependencyGraph]:
        ttl = max(1, int(getattr(settings, "graph_v21_cache_ttl_seconds", 45)))
        now = monotonic()
        with self._graph_cache_lock:
            cached = self._graph_cache.get(key)
            if not cached:
                return None
            ts, payload = cached
            if now - ts > ttl:
                self._graph_cache.pop(key, None)
                return None
            return payload.model_copy(deep=True)

    def _set_cached_graph(self, key: str, payload: DependencyGraph) -> None:
        max_entries = max(8, int(getattr(settings, "graph_v21_cache_max_entries", 64)))
        now = monotonic()
        with self._graph_cache_lock:
            self._graph_cache[key] = (now, payload.model_copy(deep=True))
            if len(self._graph_cache) <= max_entries:
                return
            # Drop oldest entries first.
            stale_keys = sorted(self._graph_cache.items(), key=lambda item: item[1][0])[: len(self._graph_cache) - max_entries]
            for stale_key, _ in stale_keys:
                self._graph_cache.pop(stale_key, None)

    def _module_key_for_path(self, path: str) -> str:
        parts = [segment for segment in path.split("/") if segment]
        if len(parts) >= 4 and parts[0] in {"apps", "packages"} and parts[2] == "src":
            return "/".join(parts[:4])
        if len(parts) >= 2 and parts[0] in {"apps", "packages"}:
            return "/".join(parts[:2])
        if len(parts) >= 2 and parts[0] == "src":
            return "/".join(parts[:2])
        if len(parts) >= 2 and parts[0] in {"scripts", "tools", "config", "configs", ".github", ".opencode", ".agents"}:
            return parts[0]
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return "root"

    def _build_module_graph(
        self,
        file_nodes: List[GraphNode],
        file_edges: List[GraphEdge],
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        module_members: Dict[str, List[GraphNode]] = defaultdict(list)
        for node in file_nodes:
            module_members[self._module_key_for_path(node.id)].append(node)

        internal_edge_totals: Dict[str, int] = defaultdict(int)
        external_edge_totals: Dict[str, int] = defaultdict(int)
        module_pair_edge_totals: Dict[Tuple[str, str, str], Dict[str, float]] = {}
        for edge in file_edges:
            source_module = self._module_key_for_path(edge.source)
            target_module = self._module_key_for_path(edge.target)
            weight = max(1, edge.weight or 1)
            relation = edge.relation or edge.type or "imports"
            if source_module == target_module:
                internal_edge_totals[source_module] += weight
                continue

            external_edge_totals[source_module] += weight
            external_edge_totals[target_module] += weight
            key = (source_module, target_module, relation)
            if key not in module_pair_edge_totals:
                module_pair_edge_totals[key] = {"count": 0, "confidence": 0.0}
            module_pair_edge_totals[key]["count"] += weight
            module_pair_edge_totals[key]["confidence"] = max(
                module_pair_edge_totals[key]["confidence"],
                edge.confidence or 0.0,
            )

        module_nodes: List[GraphNode] = []
        for module_id in sorted(module_members.keys()):
            members = module_members[module_id]
            type_counts = Counter((member.type or "file") for member in members)
            dominant_types = [item[0] for item in type_counts.most_common(3)]
            loc_total = sum(member.loc or 0 for member in members)
            top_members = sorted(
                members,
                key=lambda item: (-(item.importance or 0), item.id),
            )[:5]
            member_count = len(members)
            internal_edge_count = int(internal_edge_totals.get(module_id, 0))
            external_edge_count = int(external_edge_totals.get(module_id, 0))
            if member_count <= 1:
                internal_density = 0.0
            else:
                internal_density = round(internal_edge_count / float(member_count * (member_count - 1)), 4)
            module_nodes.append(
                GraphNode(
                    id=module_id,
                    label=module_id.split("/")[-1] or module_id,
                    type=dominant_types[0] if dominant_types else "file",
                    description=f"{len(members)} files in {module_id}",
                    entity="module",
                    group="/".join(module_id.split("/")[:2]) if "/" in module_id else module_id,
                    importance=max((member.importance or 1) for member in members),
                    loc=loc_total,
                    loc_total=loc_total,
                    member_count=member_count,
                    dominant_types=dominant_types,
                    top_files=[member.id for member in top_members],
                    module_key=module_id,
                    internal_edge_count=internal_edge_count,
                    external_edge_count=external_edge_count,
                    internal_density=internal_density,
                )
            )

        module_edges: List[GraphEdge] = []
        for (source, target, relation), metrics in module_pair_edge_totals.items():
            aggregated = int(metrics["count"])
            weight = min(5, max(1, round(aggregated / 3)))
            module_edges.append(
                GraphEdge(
                    source=source,
                    target=target,
                    label=relation,
                    type=relation,
                    relation=relation,
                    weight=weight,
                    confidence=round(float(metrics["confidence"]), 2),
                    aggregated_count=aggregated,
                )
            )

        return module_nodes, module_edges

    def _extract_scoped_file_subgraph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        scope: str,
        hops: int = 1,
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        scope = (scope or "").strip()
        if not scope:
            return nodes, edges

        seeds = {
            node.id
            for node in nodes
            if node.entity in {None, "file"} and self._module_key_for_path(node.id) == scope
        }
        if not seeds:
            return nodes, edges

        include = set(seeds)
        for _ in range(max(1, hops)):
            frontier_additions: Set[str] = set()
            for edge in edges:
                if edge.source in include:
                    frontier_additions.add(edge.target)
                if edge.target in include:
                    frontier_additions.add(edge.source)
            include.update(frontier_additions)

        filtered_nodes = [node for node in nodes if node.id in include]
        filtered_edges = [edge for edge in edges if edge.source in include and edge.target in include]
        if not filtered_nodes:
            return nodes, edges
        # Ensure deterministic ordering even before final sort.
        return sorted(filtered_nodes, key=lambda item: item.id), sorted(
            filtered_edges,
            key=lambda item: (item.source, item.target, item.relation or item.type or "imports"),
        )

    def _extract_focus_subgraph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        focus_node: str,
        hops: int = 1,
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        focus_node = (focus_node or "").strip()
        if not focus_node:
            return nodes, edges

        node_ids = {node.id for node in nodes}
        if focus_node not in node_ids:
            return nodes, edges

        include = {focus_node}
        for _ in range(max(1, hops)):
            frontier: Set[str] = set()
            for edge in edges:
                if edge.source in include:
                    frontier.add(edge.target)
                if edge.target in include:
                    frontier.add(edge.source)
            include.update(frontier)

        filtered_nodes = [node for node in nodes if node.id in include]
        filtered_edges = [edge for edge in edges if edge.source in include and edge.target in include]
        return filtered_nodes, filtered_edges

    def _rank_edges(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
    ) -> List[GraphEdge]:
        node_map = {node.id: node for node in nodes}
        max_degree = max((node.metrics.degree if node.metrics else 0) for node in nodes) if nodes else 0
        ranked_edges: List[GraphEdge] = []

        for edge in edges:
            source_node = node_map.get(edge.source)
            target_node = node_map.get(edge.target)
            if not source_node or not target_node:
                continue

            weight_norm = min(1.0, float(edge.weight or 1) / 5.0)
            confidence = max(0.0, min(1.0, float(edge.confidence or 0.6)))
            if max_degree > 0:
                source_degree = float(source_node.metrics.degree if source_node.metrics else 0)
                target_degree = float(target_node.metrics.degree if target_node.metrics else 0)
                degree_norm = min(1.0, ((source_degree + target_degree) / 2.0) / float(max_degree))
            else:
                degree_norm = 0.0
            bridge_bonus = 1.0 if (source_node.group or "") != (target_node.group or "") else 0.0
            rank = (0.45 * weight_norm) + (0.25 * confidence) + (0.20 * degree_norm) + (0.10 * bridge_bonus)
            edge.rank = round(rank, 4)
            ranked_edges.append(edge)

        return ranked_edges

    def _apply_per_node_edge_budget(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        per_node_limit: int,
    ) -> List[GraphEdge]:
        if per_node_limit <= 0 or not edges:
            return edges

        node_ids = {node.id for node in nodes}
        incident: Dict[str, List[GraphEdge]] = defaultdict(list)
        for edge in edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                continue
            incident[edge.source].append(edge)
            incident[edge.target].append(edge)

        keep_edge_ids: Set[str] = set()
        for node_id, node_edges in incident.items():
            _ = node_id
            ranked = sorted(
                node_edges,
                key=lambda edge: (
                    -(edge.rank or 0.0),
                    -(edge.weight or 1),
                    -(edge.confidence or 0.0),
                    edge.source,
                    edge.target,
                    edge.relation or edge.type or "imports",
                ),
            )
            for edge in ranked[:per_node_limit]:
                keep_edge_ids.add(f"{edge.source}|{edge.target}|{edge.relation or edge.type or 'imports'}")

        filtered = [
            edge
            for edge in edges
            if f"{edge.source}|{edge.target}|{edge.relation or edge.type or 'imports'}" in keep_edge_ids
        ]
        return filtered

    def _build_graph_node_from_file(self, path: str, code_file: CodeFile) -> GraphNode:
        label = Path(path).name or path
        return GraphNode(
            id=path,
            label=label,
            type=self._classify_path(path),
            description=f"{label} in {self._derive_group(path)}",
            entity="file",
            group=self._derive_group(path),
            loc=code_file.line_count or 0,
            exports=(code_file.exports or [])[:6],
            module_key=self._module_key_for_path(path),
        )

    def _build_deterministic_edges(
        self,
        repo: Repository,
        source_paths: List[str],
        all_paths: Set[str],
        file_map: Dict[str, CodeFile],
    ) -> List[GraphEdge]:
        repo_root = Path(repo.local_path) if repo.local_path else None
        edge_index: Dict[Tuple[str, str, str], Dict[str, float]] = {}

        for source in sorted(source_paths):
            modules: Set[str] = set()
            if repo_root:
                abs_path = repo_root / source
                if abs_path.exists():
                    try:
                        content = abs_path.read_text(encoding="utf-8", errors="ignore")
                        modules = self._extract_modules_from_content(content)
                    except Exception:
                        modules = set()

            if not modules:
                modules = self._extract_modules_from_import_strings((file_map.get(source).imports or []) if source in file_map else [])

            for module in sorted(modules):
                resolved = self._resolve_module_path(source, module, all_paths, repo_root)
                if not resolved or resolved == source:
                    continue

                relation = self._infer_relation(source, resolved, module)
                key = (source, resolved, relation)
                confidence = 0.92 if module.startswith(".") else 0.78 if module.startswith("@") else 0.72

                if key not in edge_index:
                    edge_index[key] = {"count": 0, "confidence": confidence}
                edge_index[key]["count"] += 1
                edge_index[key]["confidence"] = max(edge_index[key]["confidence"], confidence)

        edges: List[GraphEdge] = []
        for (source, target, relation), metrics in edge_index.items():
            weight = min(5, 1 + int(metrics["count"] // 2))
            edges.append(
                GraphEdge(
                    source=source,
                    target=target,
                    label=relation,
                    type=relation,
                    relation=relation,
                    weight=weight,
                    confidence=round(float(metrics["confidence"]), 2),
                )
            )
        return edges

    def _extract_modules_from_content(self, content: str) -> Set[str]:
        modules: Set[str] = set()
        for pattern in self.IMPORT_PATTERNS:
            for match in re.findall(pattern, content, re.MULTILINE):
                cleaned = (match or "").strip()
                if cleaned:
                    modules.add(cleaned)
        return modules

    def _extract_modules_from_import_strings(self, imports: List[str]) -> Set[str]:
        modules: Set[str] = set()
        for statement in imports or []:
            for pattern in self.IMPORT_PATTERNS:
                for match in re.findall(pattern, statement or "", re.MULTILINE):
                    cleaned = (match or "").strip()
                    if cleaned:
                        modules.add(cleaned)
        return modules

    def _apply_node_metrics(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        node_ids = {node.id for node in nodes}
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)

        filtered_edges: List[GraphEdge] = []
        for edge in edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                continue
            out_degree[edge.source] += 1
            in_degree[edge.target] += 1
            filtered_edges.append(edge)

        max_possible = max(1, len(node_ids) - 1)
        for node in nodes:
            in_count = in_degree[node.id]
            out_count = out_degree[node.id]
            degree = in_count + out_count
            centrality = round(degree / max_possible, 4)
            loc_score = min(3.0, log1p(node.loc or 0) / 4.0)
            importance = max(1, min(10, round(1 + (centrality * 7.0) + loc_score)))
            node.metrics = GraphNodeMetrics(
                in_degree=in_count,
                out_degree=out_count,
                degree=degree,
                centrality=centrality,
            )
            node.importance = importance

        return nodes, filtered_edges

    def _prune_graph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        max_nodes: int,
        filter_orphans: bool = True,
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        if len(nodes) <= max_nodes:
            return nodes, edges

        node_map = {node.id: node for node in nodes}
        components = self._connected_components(set(node_map.keys()), edges)
        if not components:
            top_nodes = sorted(nodes, key=lambda node: (-self._score_node_for_pruning(node, edges), node.id))[:max_nodes]
            keep_ids = {node.id for node in top_nodes}
            return self._filter_to_nodes(nodes, edges, keep_ids, filter_orphans=filter_orphans)

        keep_ids: Set[str] = set()
        for component in sorted(components, key=lambda comp: (-len(comp), sorted(comp)[0])):
            if len(keep_ids) >= max_nodes:
                break
            remaining = max_nodes - len(keep_ids)
            if len(component) <= remaining:
                keep_ids.update(component)
                continue

            scored = sorted(
                component,
                key=lambda node_id: (
                    -self._score_node_for_pruning(node_map[node_id], edges),
                    node_id,
                ),
            )
            keep_ids.update(scored[:remaining])

        return self._filter_to_nodes(nodes, edges, keep_ids, filter_orphans=filter_orphans)

    def _score_node_for_pruning(self, node: GraphNode, edges: List[GraphEdge]) -> float:
        degree = node.metrics.degree if node.metrics else 0
        centrality = node.metrics.centrality if node.metrics else 0.0
        group_bridges = set()
        for edge in edges:
            if edge.source == node.id:
                group_bridges.add(edge.target.split("/")[0])
            elif edge.target == node.id:
                group_bridges.add(edge.source.split("/")[0])
        bridge_bonus = 4.0 if len(group_bridges) >= 2 else 0.0
        loc_bonus = min(2.0, log1p(node.loc or 0) / 5.0)
        entrypoint_bonus = 2.0 if any(
            token in node.label.lower() for token in ["index.", "app.", "main.", "router", "route", "layout"]
        ) else 0.0
        return (degree * 2.5) + (centrality * 6.0) + bridge_bonus + loc_bonus + entrypoint_bonus

    def _connected_components(self, node_ids: Set[str], edges: List[GraphEdge]) -> List[Set[str]]:
        adjacency: Dict[str, Set[str]] = {node_id: set() for node_id in node_ids}
        for edge in edges:
            if edge.source in adjacency and edge.target in adjacency:
                adjacency[edge.source].add(edge.target)
                adjacency[edge.target].add(edge.source)

        seen: Set[str] = set()
        components: List[Set[str]] = []
        for start in sorted(node_ids):
            if start in seen:
                continue
            queue = deque([start])
            component: Set[str] = set()
            seen.add(start)
            while queue:
                current = queue.popleft()
                component.add(current)
                for neighbor in sorted(adjacency[current]):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append(neighbor)
            components.append(component)
        return components

    def _filter_to_nodes(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        keep_ids: Set[str],
        filter_orphans: bool = True,
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        filtered_nodes = [node for node in nodes if node.id in keep_ids]
        filtered_edges = [edge for edge in edges if edge.source in keep_ids and edge.target in keep_ids]
        if filter_orphans and not settings.graph_include_orphans:
            filtered_nodes, filtered_edges = self._filter_connected_nodes(filtered_nodes, filtered_edges)
        return filtered_nodes, filtered_edges

    def _compute_graph_stats(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> GraphStats:
        node_count = len(nodes)
        edge_count = len(edges)
        if node_count <= 1:
            density = 0.0
        else:
            density = round(edge_count / (node_count * (node_count - 1)), 4)
        clusters = len({node.group for node in nodes if node.group}) or 1 if node_count > 0 else 0
        return GraphStats(nodes=node_count, edges=edge_count, clusters=clusters, density=density)

    def _filter_connected_nodes(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Remove nodes and edges that are disconnected from the final graph."""
        connected_ids: Set[str] = set()
        for edge in edges:
            connected_ids.add(edge.source)
            connected_ids.add(edge.target)

        filtered_nodes = [node for node in nodes if node.id in connected_ids]
        valid_ids = {node.id for node in filtered_nodes}
        filtered_edges = [edge for edge in edges if edge.source in valid_ids and edge.target in valid_ids]
        return filtered_nodes, filtered_edges

    async def _maybe_enrich_nodes_with_llm(self, repo_id: str, nodes: List[GraphNode]) -> bool:
        if not bool(getattr(settings, "graph_v2_enrich_descriptions", False)):
            return False
        if not nodes:
            return False

        top_k = max(6, int(getattr(settings, "graph_v2_enrich_top_k", 24)))
        focus_nodes = sorted(
            nodes,
            key=lambda node: (-(node.importance or 0), node.id),
        )[:top_k]

        prompt = {
            "instructions": (
                "Write concise architecture descriptions for these code files. "
                "Return JSON: {\"descriptions\": [{\"id\": \"...\", \"description\": \"...\"}]}. "
                "Each description must be <= 18 words."
            ),
            "repo_id": repo_id,
            "nodes": [
                {"id": node.id, "type": node.type, "group": node.group, "label": node.label}
                for node in focus_nodes
            ],
        }

        try:
            raw = await self._llm.generate(
                [
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": json.dumps(prompt)},
                ],
                max_tokens=min(settings.graph_max_tokens, 700),
                timeout=settings.graph_llm_timeout_seconds,
                temperature=0.0,
                use_cache=settings.demo_mode,
            )
            cleaned = self._extract_json_block(raw)
            data = json.loads(self._repair_json_like(cleaned))
            description_map = {
                item.get("id"): item.get("description")
                for item in data.get("descriptions", [])
                if item.get("id") and item.get("description")
            }
            for node in nodes:
                desc = description_map.get(node.id)
                if desc:
                    node.description = str(desc)[:200]
            return bool(description_map)
        except Exception:
            return False

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

    def _classify_path(self, path: str) -> str:
        p = path.lower()
        name = Path(path).name.lower()
        if "/components/" in p or name.endswith(".tsx") and "page." not in name and "layout." not in name:
            return "component"
        if "/pages/" in p or "/app/" in p and ("page." in name or "layout." in name):
            return "page"
        if "store" in p or "zustand" in p or "redux" in p:
            return "store"
        if "route" in p or "router" in p or "/api/" in p or "service" in p:
            return "api"
        if "config" in p or "settings" in p:
            return "config"
        if "util" in p or "helper" in p or "common" in p or "/lib/" in p:
            return "util"
        if "model" in p or "schema" in p or "types" in p:
            return "schema"
        return "file"

    def _derive_group(self, path: str) -> str:
        parts = [part for part in Path(path).parts if part not in {"", "."}]
        if not parts:
            return "root"
        if len(parts) >= 3 and parts[0] in {"src", "apps"}:
            return "/".join(parts[:2])
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return parts[0]

    def _infer_relation(self, source_path: str, target_path: str, module_path: str) -> str:
        s = source_path.lower()
        t = target_path.lower()
        m = module_path.lower()
        if "config" in s or "config" in t:
            return "configures"
        if "api" in s or "service" in s:
            return "calls"
        if ".d.ts" in t or "types" in t:
            return "uses"
        if "extends" in m or "base" in m:
            return "extends"
        return "imports"

    def _resolve_module_path(
        self,
        source_path: str,
        module_path: str,
        all_paths: Set[str],
        repo_root: Optional[Path],
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

        # Normalize aliases/root-relative imports while preserving intent for candidate ordering.
        mod = module_path
        is_alias_import = module_path.startswith("@/")
        if mod.startswith("@/"):
            mod = mod[2:]  # drop "@/"
        elif mod.startswith("/"):
            mod = mod[1:]

        candidates: List[str] = []

        # Relative path from current file
        if module_path.startswith("."):
            candidates.append((base_dir / module_path).as_posix())
        else:
            normalized_mod = mod.lstrip("/")

            # Primary repo-relative candidate.
            if normalized_mod:
                candidates.append(normalized_mod)

            # Common TS/JS alias convention: "@/*" points to "src/*".
            if is_alias_import and normalized_mod and not normalized_mod.startswith("src/"):
                candidates.append(f"src/{normalized_mod}")

            # Best-effort for bare absolute-ish imports in monorepos.
            if normalized_mod and not normalized_mod.startswith(("src/", "apps/")):
                candidates.append(f"src/{normalized_mod}")

            # Keep repo_root for compatibility/future expansion; we still resolve against repo-relative all_paths.
            if repo_root and normalized_mod:
                candidates.append((repo_root / normalized_mod).as_posix().replace(repo_root.as_posix() + "/", ""))

        exts = self.GRAPH_IMPORT_EXTENSIONS

        for raw_candidate in candidates:
            cand = posixpath.normpath(raw_candidate).lstrip("./")
            if cand.startswith("../"):
                continue
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

    async def export_lesson_to_codetour(
        self,
        repo_id: str,
        lesson_id: str,
        persona_id: Optional[str] = None,
    ) -> Optional[CodeTour]:
        """Export a lesson as a VS Code CodeTour."""
        persona = self._normalize_persona(persona_id or "new_hire")
        lesson_title = self._resolve_lesson_title(repo_id, lesson_id, persona) or f"Lesson {lesson_id}"

        # 2. Generate (or fetch) lesson content
        content = await self.generate_lesson(
            repo_id=repo_id,
            lesson_id=lesson_id,
            lesson_title=lesson_title,
            persona_id=persona,
        )

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
