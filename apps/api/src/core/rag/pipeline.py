"""
RAG pipeline for chat over code repositories.
Adds intent-aware retrieval, content-aware reranking, and prompt routing.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional

from src.config import settings
from src.core.cache.chat_cache import ChatCache

logger = logging.getLogger(__name__)


class ChatIntent(str, Enum):
    OVERVIEW = "overview"
    IMPLEMENTATION = "implementation"
    TECH_STACK = "tech_stack"
    LOCATION = "location"
    TROUBLESHOOTING = "troubleshooting"


class RetrievalProfile(str, Enum):
    DOCS_FIRST = "docs_first"
    CODE_FIRST = "code_first"
    STACK = "stack"
    LOCATION = "location"
    ERROR = "error_focus"


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector store."""

    id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    chunk_name: str
    score: float
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class RetrievalDiagnostics:
    """Diagnostics for retrieval observability and offline eval."""

    intent: str
    profile: str
    expanded_queries: List[str]
    candidate_count: int
    reranked: bool
    retrieval_time_ms: float
    rerank_time_ms: float
    cache_hit: bool
    grounding: str


@dataclass
class RetrievalResult:
    """Result of retrieval phase."""

    chunks: List[RetrievedChunk]
    query: str
    intent: str
    profile: str
    diagnostics: RetrievalDiagnostics


class RAGPipeline:
    """RAG pipeline with intent routing and robust grounding."""

    QUERY_EXPANSIONS = {
        "how does": ["implementation", "flow", "logic", "function"],
        "where is": ["file", "path", "location", "defined"],
        "error": ["exception", "traceback", "retry", "fallback"],
        "auth": ["authentication", "authorization", "login", "session", "token"],
        "database": ["schema", "model", "query", "migration"],
        "feature": ["overview", "purpose", "capabilities", "use case"],
        "stack": ["framework", "library", "dependency", "architecture"],
    }

    SYSTEM_PROMPTS: Dict[ChatIntent, str] = {
        ChatIntent.OVERVIEW: """You are an expert assistant for understanding software products from repository evidence.

Rules:
1. For high-level feature/overview questions, prioritize README/docs evidence before code internals.
2. Do NOT infer product features only from package dependencies unless docs are absent; state uncertainty clearly.
3. Cite concrete evidence paths with line ranges whenever possible.
4. Keep answer concise, factual, and source-grounded.

Structure:
1. Direct answer (1-2 sentences)
2. Main features (bulleted)
3. Evidence (files and citations)
4. Notes on confidence/unknowns

Repository context:
{context}""",
        ChatIntent.IMPLEMENTATION: """You are an expert code assistant helping developers understand implementation details.

Rules:
1. Start with a direct technical answer.
2. Reference exact files/functions/classes and behavior.
3. Include short code snippets with language fences when relevant.
4. Cite sources as `path:Ll-Lm`.
5. If uncertain, say what is missing.

Repository context:
{context}""",
        ChatIntent.TECH_STACK: """You are an expert assistant summarizing repository tech stack.

Rules:
1. Use docs + manifests (package.json/pyproject/requirements/etc) as primary evidence.
2. Distinguish core runtime stack vs tooling/dev dependencies.
3. Avoid over-claiming from a single file.
4. Cite evidence as `path:Ll-Lm`.

Repository context:
{context}""",
        ChatIntent.LOCATION: """You are an expert code navigation assistant.

Rules:
1. Answer with likely file paths first.
2. Then explain why each location is relevant.
3. Include concise snippets for proof.
4. Cite evidence as `path:Ll-Lm`.

Repository context:
{context}""",
        ChatIntent.TROUBLESHOOTING: """You are an expert debugging assistant.

Rules:
1. Focus on root-cause hypotheses grounded in retrieved code/docs.
2. Provide likely failure points and concrete checks.
3. Separate confirmed facts from hypotheses.
4. Cite evidence as `path:Ll-Lm`.

Repository context:
{context}""",
    }

    def __init__(self, vector_store, llm_service, repo_id: str, chat_cache: Optional[ChatCache] = None):
        self._vector_store = vector_store
        self._llm = llm_service
        self._repo_id = repo_id
        self._chat_cache = chat_cache

    def classify_intent(self, query: str, mode: str = "auto") -> ChatIntent:
        """Classify user intent with deterministic rules."""
        if mode and mode != "auto":
            try:
                return ChatIntent(mode)
            except ValueError:
                logger.warning("Unknown chat mode '%s', defaulting to auto intent", mode)

        ordered = self._score_intents(query)
        best_intent, best_score = ordered[0]
        if best_score == 0:
            return ChatIntent.IMPLEMENTATION
        return best_intent

    def _score_intents(self, query: str) -> List[tuple[ChatIntent, int]]:
        query_lower = query.lower()
        scores = {intent: 0 for intent in ChatIntent}

        overview_patterns = [
            "main features",
            "what does this application",
            "what is this application",
            "overview",
            "about",
            "purpose",
            "capabilities",
        ]
        implementation_patterns = [
            "how does",
            "how is",
            "implementation",
            "flow",
            "code path",
            "internals",
        ]
        tech_stack_patterns = [
            "tech stack",
            "technologies",
            "libraries",
            "dependencies",
            "frameworks",
            "stack",
        ]
        location_patterns = [
            "where is",
            "which file",
            "location",
            "defined",
            "find",
            "located",
        ]
        troubleshooting_patterns = [
            "error",
            "bug",
            "failing",
            "not working",
            "exception",
            "fix",
            "issue",
        ]

        def add_score(patterns: List[str], intent: ChatIntent, points: int = 2) -> None:
            for pattern in patterns:
                if pattern in query_lower:
                    scores[intent] += points

        add_score(overview_patterns, ChatIntent.OVERVIEW, 3)
        add_score(implementation_patterns, ChatIntent.IMPLEMENTATION, 3)
        add_score(tech_stack_patterns, ChatIntent.TECH_STACK, 3)
        add_score(location_patterns, ChatIntent.LOCATION, 3)
        add_score(troubleshooting_patterns, ChatIntent.TROUBLESHOOTING, 3)

        if re.search(r"\b(feature|overview|purpose)\b", query_lower):
            scores[ChatIntent.OVERVIEW] += 2
        if re.search(r"\b(api|handler|service|class|function|method)\b", query_lower):
            scores[ChatIntent.IMPLEMENTATION] += 1
        if re.search(r"\b(config|package\.json|pyproject|requirements)\b", query_lower):
            scores[ChatIntent.TECH_STACK] += 1

        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    async def _llm_intent_tiebreak(self, query: str, candidates: List[ChatIntent]) -> Optional[ChatIntent]:
        if not candidates:
            return None
        try:
            allowed = ", ".join(candidate.value for candidate in candidates)
            prompt = (
                "Classify this user question into one intent.\n"
                f"Question: {query}\n"
                f"Allowed intents: {allowed}\n"
                "Return only one intent string from the allowed list."
            )
            response = await self._llm.generate([{"role": "user", "content": prompt}], use_cache=False)
            lowered = response.lower()
            for candidate in candidates:
                if candidate.value in lowered:
                    return candidate
        except Exception as exc:
            logger.warning("Intent LLM tiebreak failed: %s", exc)
        return None

    async def classify_intent_async(self, query: str, mode: str = "auto") -> ChatIntent:
        if mode and mode != "auto":
            try:
                return ChatIntent(mode)
            except ValueError:
                logger.warning("Unknown chat mode '%s', defaulting to auto intent", mode)

        ordered = self._score_intents(query)
        best_intent, best_score = ordered[0]
        if best_score == 0:
            return ChatIntent.IMPLEMENTATION

        if settings.chat_intent_llm_tiebreak_enabled and len(ordered) > 1 and ordered[1][1] == best_score:
            candidates = [item[0] for item in ordered[:3] if item[1] == best_score]
            guessed = await self._llm_intent_tiebreak(query=query, candidates=candidates)
            if guessed:
                return guessed

        return best_intent

    def _intent_profile(self, intent: ChatIntent) -> RetrievalProfile:
        if intent == ChatIntent.OVERVIEW:
            if settings.chat_docs_first_overview_enabled:
                return RetrievalProfile.DOCS_FIRST
            return RetrievalProfile.CODE_FIRST
        if intent == ChatIntent.TECH_STACK:
            return RetrievalProfile.STACK
        if intent == ChatIntent.LOCATION:
            return RetrievalProfile.LOCATION
        if intent == ChatIntent.TROUBLESHOOTING:
            return RetrievalProfile.ERROR
        return RetrievalProfile.CODE_FIRST

    def _normalize_query(self, query: str) -> str:
        lowered = query.lower()
        lowered = re.sub(r"[^a-z0-9_\-./ ]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _is_explicit_entrypoint_question(self, query_lower: str) -> bool:
        return bool(re.search(r"\b(entry point|startup|bootstrap|main file|main entry)\b", query_lower))

    def _expand_query(self, query: str, intent: ChatIntent) -> List[str]:
        """Expand query with intent-aware synonyms and controlled heuristics."""
        queries = [query]
        query_lower = query.lower()

        for keyword, expansions in self.QUERY_EXPANSIONS.items():
            if keyword in query_lower:
                for expansion in expansions[:2]:
                    expanded = f"{query} {expansion}"
                    if expanded not in queries:
                        queries.append(expanded)

        if intent == ChatIntent.OVERVIEW:
            queries.extend(
                [
                    f"{query} README overview",
                    f"{query} docs",
                ]
            )
        elif intent == ChatIntent.TECH_STACK:
            queries.extend(
                [
                    f"{query} package.json dependencies",
                    f"{query} requirements pyproject",
                ]
            )
        elif self._is_explicit_entrypoint_question(query_lower):
            queries.extend(
                [
                    "index.ts OR index.js OR main.py OR app.tsx OR server.ts",
                    "package.json main",
                ]
            )

        deduped: List[str] = []
        for q in queries:
            if q not in deduped:
                deduped.append(q)
        return deduped[:6]

    async def _embed_query_cached(self, query: str) -> List[float]:
        embedding_service = self._vector_store._embedding_service
        embedding_model = getattr(embedding_service, "_model", embedding_service.__class__.__name__)

        if self._chat_cache:
            cached = await self._chat_cache.get_embedding(query=query, model=embedding_model)
            if cached is not None:
                return cached

        embedding = await embedding_service.embed_query(query)

        if self._chat_cache:
            await self._chat_cache.set_embedding(query=query, model=embedding_model, embedding=embedding)

        return embedding

    def _serialize_chunk(self, chunk: RetrievedChunk) -> Dict[str, object]:
        return {
            "id": chunk.id,
            "content": chunk.content,
            "file_path": chunk.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "chunk_type": chunk.chunk_type,
            "chunk_name": chunk.chunk_name,
            "score": chunk.score,
            "metadata": chunk.metadata,
        }

    def _deserialize_chunk(self, item: Dict[str, object]) -> RetrievedChunk:
        return RetrievedChunk(
            id=str(item.get("id", "")),
            content=str(item.get("content", "")),
            file_path=str(item.get("file_path", "")),
            start_line=int(item.get("start_line", 0)),
            end_line=int(item.get("end_line", 0)),
            chunk_type=str(item.get("chunk_type", "unknown")),
            chunk_name=str(item.get("chunk_name", "")),
            score=float(item.get("score", 0.0)),
            metadata=dict(item.get("metadata", {})),
        )

    def _is_docs_path(self, file_path: str) -> bool:
        path = file_path.lower()
        return (
            path.endswith("readme.md")
            or path.endswith("readme")
            or path.startswith("docs/")
            or "/docs/" in path
            or path.endswith(".md")
            or path.endswith(".mdx")
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 6,
        mode: str = "auto",
        context_files: Optional[List[str]] = None,
    ) -> RetrievalResult:
        """Intent-aware retrieval with caching and content reranking."""
        started = time.perf_counter()
        intent = (
            await self.classify_intent_async(query=query, mode=mode)
            if settings.chat_intent_routing_enabled
            else ChatIntent.IMPLEMENTATION
        )
        profile = self._intent_profile(intent)
        normalized_query = self._normalize_query(query)
        expanded_queries = self._expand_query(query, intent)
        cache_hit = False

        retrieval_limit = max(limit * 3, settings.chat_retrieval_candidate_limit)
        all_chunks: Dict[str, RetrievedChunk] = {}

        # Retrieval cache lookup
        if self._chat_cache:
            cached_candidates = await self._chat_cache.get_retrieval(
                repo_id=self._repo_id,
                normalized_query=normalized_query,
                intent=intent.value,
                profile=profile.value,
                context_files=context_files,
            )
            if cached_candidates:
                cache_hit = True
                for candidate in cached_candidates:
                    chunk = self._deserialize_chunk(candidate)
                    all_chunks[chunk.id] = chunk

        if not all_chunks:
            for expanded in expanded_queries:
                query_embedding = await self._embed_query_cached(expanded)
                results = await self._vector_store.hybrid_search(
                    collection_name=self._repo_id,
                    query_embedding=query_embedding,
                    query_text=expanded,
                    limit=retrieval_limit,
                    profile=profile.value,
                    path_allowlist=context_files,
                )

                for result in results:
                    chunk = RetrievedChunk(
                        id=result.id,
                        content=result.content,
                        file_path=result.metadata.get("file_path", ""),
                        start_line=result.metadata.get("start_line", 0),
                        end_line=result.metadata.get("end_line", 0),
                        chunk_type=result.metadata.get("chunk_type", "unknown"),
                        chunk_name=result.metadata.get("chunk_name", ""),
                        score=result.score,
                        metadata=result.metadata,
                    )
                    previous = all_chunks.get(chunk.id)
                    if previous is None or chunk.score > previous.score:
                        all_chunks[chunk.id] = chunk

            if self._chat_cache and all_chunks:
                to_cache = [self._serialize_chunk(c) for c in sorted(all_chunks.values(), key=lambda item: item.score, reverse=True)[:retrieval_limit]]
                await self._chat_cache.set_retrieval(
                    repo_id=self._repo_id,
                    normalized_query=normalized_query,
                    intent=intent.value,
                    profile=profile.value,
                    context_files=context_files,
                    candidates=to_cache,
                )

        chunks = sorted(all_chunks.values(), key=lambda item: item.score, reverse=True)[:retrieval_limit]

        rerank_started = time.perf_counter()
        reranked = False
        if settings.chat_content_rerank_enabled and len(chunks) > 5:
            candidate_limit = max(6, settings.chat_rerank_candidate_limit)
            primary = chunks[:candidate_limit]
            secondary = chunks[candidate_limit:]
            reordered = await self._rerank_chunks(query=query, intent=intent, chunks=primary)
            chunks = reordered + secondary
            reranked = True
        rerank_elapsed_ms = (time.perf_counter() - rerank_started) * 1000

        selected = chunks[:limit]
        docs_hits = sum(1 for chunk in selected if self._is_docs_path(chunk.file_path))
        if intent == ChatIntent.OVERVIEW:
            grounding = "high" if docs_hits >= 1 else "medium" if selected else "low"
        else:
            grounding = "high" if selected else "low"

        diagnostics = RetrievalDiagnostics(
            intent=intent.value,
            profile=profile.value,
            expanded_queries=expanded_queries,
            candidate_count=len(chunks),
            reranked=reranked,
            retrieval_time_ms=(time.perf_counter() - started) * 1000,
            rerank_time_ms=rerank_elapsed_ms,
            cache_hit=cache_hit,
            grounding=grounding,
        )

        logger.info(
            "Retrieval complete repo=%s intent=%s profile=%s cache_hit=%s candidates=%s selected=%s grounding=%s",
            self._repo_id,
            intent.value,
            profile.value,
            cache_hit,
            len(chunks),
            len(selected),
            grounding,
        )

        return RetrievalResult(
            chunks=selected,
            query=query,
            intent=intent.value,
            profile=profile.value,
            diagnostics=diagnostics,
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, object]]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
            cleaned = cleaned.rstrip("`").strip()

        try:
            payload = json.loads(cleaned)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            return None
        return None

    async def _rerank_chunks(
        self,
        query: str,
        intent: ChatIntent,
        chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """Rerank chunks using chunk content + metadata."""
        try:
            valid_ids = {chunk.id for chunk in chunks}
            chunk_lines = []
            for chunk in chunks:
                snippet = chunk.content.strip().replace("\n", " ")
                snippet = re.sub(r"\s+", " ", snippet)[:260]
                chunk_lines.append(
                    f"- id: {chunk.id}\n"
                    f"  file: {chunk.file_path}\n"
                    f"  type: {chunk.chunk_type}\n"
                    f"  lines: {chunk.start_line}-{chunk.end_line}\n"
                    f"  snippet: {snippet}"
                )

            prompt = (
                "Rank repository chunks by relevance to a question.\n"
                f"Question: {query}\n"
                f"Intent: {intent.value}\n"
                "Return strict JSON only in this shape: "
                '{"ranked_ids":["id1","id2","id3","id4","id5"]}\n'
                "Use only provided ids. For overview intent, prioritize README/docs with direct product descriptions.\n\n"
                "Chunks:\n"
                f"{chr(10).join(chunk_lines)}"
            )

            response = await self._llm.generate([{"role": "user", "content": prompt}], use_cache=False)
            payload = self._extract_json(response) or {}
            raw_ids = payload.get("ranked_ids", [])

            ranked_ids: List[str] = []
            if isinstance(raw_ids, list):
                for item in raw_ids:
                    if isinstance(item, str) and item in valid_ids and item not in ranked_ids:
                        ranked_ids.append(item)

            # UUID fallback if JSON parsing was imperfect.
            if not ranked_ids:
                for chunk_id in re.findall(r"[0-9a-fA-F-]{32,36}", response):
                    if chunk_id in valid_ids and chunk_id not in ranked_ids:
                        ranked_ids.append(chunk_id)

            if not ranked_ids:
                return chunks

            chunk_map = {chunk.id: chunk for chunk in chunks}
            reordered: List[RetrievedChunk] = [chunk_map[chunk_id] for chunk_id in ranked_ids if chunk_id in chunk_map]
            seen = {chunk.id for chunk in reordered}
            for chunk in chunks:
                if chunk.id not in seen:
                    reordered.append(chunk)
            return reordered
        except Exception as exc:
            logger.warning("Chunk reranking failed; using original order: %s", exc)
            return chunks

    def _language_for_file(self, file_path: str) -> str:
        lowered = file_path.lower()
        basename = lowered.rsplit("/", 1)[-1]

        if lowered.endswith((".ts", ".tsx")):
            return "typescript"
        if lowered.endswith(".py"):
            return "python"
        if lowered.endswith((".js", ".jsx")):
            return "javascript"
        if lowered.endswith(".java"):
            return "java"
        if lowered.endswith(".go"):
            return "go"
        if lowered.endswith(".rs"):
            return "rust"
        if lowered.endswith((".cs", ".csx")):
            return "csharp"
        if lowered.endswith((".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".ipp", ".tpp", ".h")):
            return "cpp"
        if lowered.endswith((".rb", ".rake", ".gemspec", ".ru")) or basename in {"gemfile", "rakefile"}:
            return "ruby"
        if lowered.endswith(".erb"):
            return "erb"
        if lowered.endswith(".json"):
            return "json"
        if lowered.endswith((".yml", ".yaml")):
            return "yaml"
        if lowered.endswith((".md", ".mdx")):
            return "markdown"
        return ""

    def _build_context(self, chunks: List[RetrievedChunk], max_chars: Optional[int] = None) -> str:
        """Build context payload grouped by file with strict size limits."""
        if not chunks:
            return "No relevant repository context found."

        budget = max_chars or settings.chat_context_max_chars
        by_file: Dict[str, List[RetrievedChunk]] = {}
        for chunk in chunks:
            by_file.setdefault(chunk.file_path, []).append(chunk)

        parts: List[str] = []
        total_chars = 0

        parts.append("### Files Referenced")
        for file_path in by_file.keys():
            parts.append(f"- `{file_path}`")
        parts.append("")

        for file_path, file_chunks in by_file.items():
            if total_chars >= budget:
                parts.append("*Context truncated due to budget.*")
                break
            parts.append(f"### {file_path}")
            for chunk in file_chunks:
                content = chunk.content.strip()
                if len(content) > 1800:
                    content = content[:1800] + "\n... [truncated]"
                lang = self._language_for_file(file_path)
                header = f"**{chunk.chunk_type.upper()}** `{chunk.chunk_name or 'unnamed'}` (L{chunk.start_line}-{chunk.end_line})"
                body = f"{header}\n```{lang}\n{content}\n```\n"
                if total_chars + len(body) > budget:
                    parts.append("*Context truncated due to budget.*")
                    total_chars = budget
                    break
                parts.append(body)
                total_chars += len(body)

        return "\n".join(parts)

    def _apply_history_budget(self, history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        if not history:
            return []

        max_tokens = max(1, settings.chat_history_max_tokens)
        approx_chars_budget = max_tokens * 4
        selected: List[Dict[str, str]] = []
        used = 0

        for message in reversed(history):
            content = str(message.get("content", ""))
            role = str(message.get("role", "user"))
            cost = max(1, len(content))
            if used + cost > approx_chars_budget:
                break
            selected.append({"role": role, "content": content})
            used += cost

        selected.reverse()
        return selected

    def _build_messages(
        self,
        query: str,
        context: RetrievalResult,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        intent = ChatIntent(context.intent)
        template = self.SYSTEM_PROMPTS.get(intent, self.SYSTEM_PROMPTS[ChatIntent.IMPLEMENTATION])
        system = template.format(context=self._build_context(context.chunks))
        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        messages.extend(self._apply_history_budget(history))
        messages.append({"role": "user", "content": query})
        return messages

    def _llm_model_name(self) -> str:
        return str(getattr(self._llm, "_model", self._llm.__class__.__name__))

    async def _get_cached_answer(self, query: str, context: RetrievalResult) -> Optional[str]:
        if not self._chat_cache:
            return None
        top_chunk_ids = [chunk.id for chunk in context.chunks[:12]]
        return await self._chat_cache.get_answer(
            repo_id=self._repo_id,
            question=query,
            intent=context.intent,
            top_chunk_ids=top_chunk_ids,
            model=self._llm_model_name(),
        )

    async def _set_cached_answer(self, query: str, context: RetrievalResult, answer: str) -> None:
        if not self._chat_cache:
            return
        top_chunk_ids = [chunk.id for chunk in context.chunks[:12]]
        await self._chat_cache.set_answer(
            repo_id=self._repo_id,
            question=query,
            intent=context.intent,
            top_chunk_ids=top_chunk_ids,
            model=self._llm_model_name(),
            answer=answer,
        )

    async def generate(
        self,
        query: str,
        context: RetrievalResult,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a non-streaming response."""
        cached = await self._get_cached_answer(query=query, context=context)
        if cached is not None:
            return cached

        messages = self._build_messages(query=query, context=context, history=history)
        result = await self._llm.generate(messages)
        await self._set_cached_answer(query=query, context=context, answer=result)
        return result

    async def generate_stream(
        self,
        query: str,
        context: RetrievalResult,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        cached = await self._get_cached_answer(query=query, context=context)
        if cached is not None:
            for i in range(0, len(cached), 320):
                yield cached[i : i + 320]
            return

        messages = self._build_messages(query=query, context=context, history=history)
        pieces: List[str] = []
        async for token in self._llm.generate_stream(messages):
            pieces.append(token)
            yield token

        if pieces:
            await self._set_cached_answer(query=query, context=context, answer="".join(pieces))
