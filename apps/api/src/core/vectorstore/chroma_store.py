"""
ChromaDB vector store implementation.
Supports semantic and hybrid search.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import chromadb
import chromadb.errors
from chromadb.config import Settings


@dataclass
class SearchResult:
    """Result from vector search."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class ChromaStore:
    """ChromaDB vector store."""

    def __init__(self, persist_directory: str, embedding_service):
        self._persist_dir = persist_directory
        self._embedding_service = embedding_service
        self._client = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def initialize(self):
        """Initialize ChromaDB client."""
        self._client = chromadb.Client(Settings(
            persist_directory=self._persist_dir,
            anonymized_telemetry=False,
            is_persistent=True,
        ))

    async def _ensure_initialized(self):
        """Lazily initialize client for non-lifespan code paths (e.g. seed scripts)."""
        if self._client is None:
            await self.initialize()

    async def close(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=True)

    async def create_collection(self, name: str, dimension: int = None):
        """Create or get a collection."""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._client.get_or_create_collection(name=name)
        )

    async def delete_collection(self, name: str):
        """Delete a collection."""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                lambda: self._client.delete_collection(name)
            )
        except (ValueError, chromadb.errors.NotFoundError):
            pass  # Collection doesn't exist, that's fine

    async def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
    ):
        """Add documents to collection."""
        await self._ensure_initialized()
        try:
            collection = self._client.get_collection(collection_name)
        except ValueError:
            raise ValueError(f"Collection '{collection_name}' not found. Create collection first.")

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            loop = asyncio.get_event_loop()
            batch_ids = ids[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            batch_documents = documents[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]

            # Fix: Capture batch values at lambda definition time using defaults
            await loop.run_in_executor(
                self._executor,
                lambda b_ids=batch_ids, b_emb=batch_embeddings, b_docs=batch_documents, b_meta=batch_metadatas:
                    collection.add(
                        ids=b_ids,
                        embeddings=b_emb,
                        documents=b_docs,
                        metadatas=b_meta,
                    )
            )

    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Search by vector similarity."""
        await self._ensure_initialized()
        try:
            collection = self._client.get_collection(collection_name)
        except ValueError:
            raise ValueError(f"Collection '{collection_name}' not found. Index the repository first.")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self._executor,
            lambda: collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 / (1 + distance)  # Convert distance to similarity

                search_results.append(SearchResult(
                    id=id,
                    score=score,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                ))

        return search_results

    async def hybrid_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        query_text: str,
        limit: int = 10,
        alpha: float = 0.5,
        profile: str = "balanced",
        path_allowlist: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Enhanced hybrid search with intent-aware boosting."""
        # Get more results for reranking
        results = await self.search(collection_name, query_embedding, limit * 4)

        query_lower = query_text.lower().strip()
        query_terms = self._normalize_query_terms(query_text)
        allowlist = [p.lower().strip() for p in (path_allowlist or []) if p.strip()]

        weight_profiles = {
            "docs_first": {
                "vector_alpha": 0.45,
                "keyword_weight": 0.18,
                "file_weight": 0.22,
                "docs_boost": 0.45,
                "manifest_boost": 0.12,
                "trivial_penalty": 0.55,
                "module_weight": 0.05,
                "symbol_weight": 0.08,
            },
            "code_first": {
                "vector_alpha": 0.65,
                "keyword_weight": 0.15,
                "file_weight": 0.18,
                "docs_boost": 0.08,
                "manifest_boost": 0.08,
                "trivial_penalty": 0.30,
                "module_weight": 0.18,
                "symbol_weight": 0.14,
            },
            "stack": {
                "vector_alpha": 0.50,
                "keyword_weight": 0.16,
                "file_weight": 0.20,
                "docs_boost": 0.22,
                "manifest_boost": 0.40,
                "trivial_penalty": 0.35,
                "module_weight": 0.08,
                "symbol_weight": 0.10,
            },
            "location": {
                "vector_alpha": 0.55,
                "keyword_weight": 0.12,
                "file_weight": 0.34,
                "docs_boost": 0.10,
                "manifest_boost": 0.12,
                "trivial_penalty": 0.25,
                "module_weight": 0.16,
                "symbol_weight": 0.08,
            },
            "error_focus": {
                "vector_alpha": 0.58,
                "keyword_weight": 0.20,
                "file_weight": 0.18,
                "docs_boost": 0.08,
                "manifest_boost": 0.10,
                "trivial_penalty": 0.25,
                "module_weight": 0.16,
                "symbol_weight": 0.14,
            },
            "balanced": {
                "vector_alpha": alpha,
                "keyword_weight": 0.15,
                "file_weight": 0.20,
                "docs_boost": 0.18,
                "manifest_boost": 0.15,
                "trivial_penalty": 0.25,
                "module_weight": 0.15,
                "symbol_weight": 0.10,
            },
        }
        weights = weight_profiles.get(profile, weight_profiles["balanced"])

        # Important file patterns for different question types
        important_patterns = {
            "entry": ["index", "main", "app", "server", "start"],
            "config": ["config", "settings", "env", ".json"],
            "route": ["route", "api", "handler", "controller"],
            "model": ["model", "schema", "type", "interface"],
        }

        boosted = []

        for r in results:
            content_lower = r.content.lower()
            file_path = r.metadata.get("file_path", "").lower()
            chunk_type = r.metadata.get("chunk_type", "")

            if allowlist and not any(allowed in file_path for allowed in allowlist):
                continue

            # Base keyword match boost
            keyword_matches = sum(1 for t in query_terms if t in content_lower)
            keyword_boost = keyword_matches * weights["keyword_weight"]

            # File path match boost
            file_boost = 0.0
            for term in query_terms:
                if term in file_path:
                    file_boost += weights["file_weight"]

            # Important file pattern boost
            pattern_boost = 0.0
            for pattern_key, patterns in important_patterns.items():
                if pattern_key in query_lower:
                    for p in patterns:
                        if p in file_path:
                            pattern_boost += 0.3
                            break

            # Chunk type relevance boost
            type_boost = 0.0
            if chunk_type == "file_summary":
                type_boost = 0.2
            elif chunk_type == "raw_file":
                type_boost = 0.2
            elif chunk_type == "module":
                type_boost = weights["module_weight"]
            elif chunk_type in ["function", "class", "method"]:
                type_boost = weights["symbol_weight"]

            docs_boost = weights["docs_boost"] if self._is_docs_path(file_path) else 0.0
            manifest_boost = weights["manifest_boost"] if self._is_manifest_path(file_path) else 0.0

            location_boost = 0.0
            if profile == "location":
                compact_query = "".join(query_terms)
                compact_path = file_path.replace("/", "")
                if compact_query and compact_query in compact_path:
                    location_boost += 0.45

            error_boost = 0.0
            if profile == "error_focus":
                if any(term in content_lower for term in ["error", "exception", "raise", "throw", "retry", "fallback"]):
                    error_boost += 0.25

            trivial_penalty = 0.0
            if self._is_trivial_chunk(content=r.content, chunk_type=chunk_type):
                trivial_penalty = weights["trivial_penalty"]

            # Calculate final score
            total_boost = keyword_boost + file_boost + pattern_boost + type_boost + docs_boost + manifest_boost + location_boost + error_boost
            vector_alpha = float(weights["vector_alpha"])
            heuristic_score = min(total_boost, 1.5)
            final_score = (vector_alpha * r.score) + ((1 - vector_alpha) * heuristic_score) - trivial_penalty

            boosted.append(SearchResult(
                id=r.id,
                score=final_score,
                content=r.content,
                metadata=r.metadata,
            ))

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted[:limit]

    def _normalize_query_terms(self, query_text: str) -> List[str]:
        stopwords = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "that",
            "the",
            "this",
            "to",
            "what",
            "where",
            "which",
            "with",
        }
        terms = re.findall(r"[a-zA-Z0-9_.-]+", query_text.lower())
        return [term for term in terms if len(term) > 1 and term not in stopwords]

    def _is_docs_path(self, file_path: str) -> bool:
        return (
            file_path.endswith("readme.md")
            or file_path.endswith("readme")
            or file_path.endswith(".md")
            or file_path.endswith(".mdx")
            or file_path.startswith("docs/")
            or "/docs/" in file_path
        )

    def _is_manifest_path(self, file_path: str) -> bool:
        return (
            file_path.endswith("package.json")
            or file_path.endswith("requirements.txt")
            or file_path.endswith("pyproject.toml")
            or file_path.endswith("go.mod")
            or file_path.endswith("cargo.toml")
            or file_path.endswith("pom.xml")
        )

    def _is_trivial_chunk(self, content: str, chunk_type: str) -> bool:
        compact = re.sub(r"\s+", " ", content.strip().lower())
        if len(compact) <= 32 and compact in {"export {};", "export {}"}:
            return True
        if chunk_type == "file_summary" and len(compact) <= 80 and compact.startswith("export"):
            return True
        return False
