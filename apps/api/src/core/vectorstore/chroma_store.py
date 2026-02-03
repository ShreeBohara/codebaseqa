"""
ChromaDB vector store implementation.
Supports semantic and hybrid search.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


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

    async def close(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=True)

    async def create_collection(self, name: str, dimension: int = None):
        """Create or get a collection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._client.get_or_create_collection(name=name)
        )

    async def delete_collection(self, name: str):
        """Delete a collection."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                lambda: self._client.delete_collection(name)
            )
        except ValueError:
            pass  # Collection doesn't exist

    async def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
    ):
        """Add documents to collection."""
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
    ) -> List[SearchResult]:
        """Enhanced hybrid search with smart boosting."""
        # Get more results for reranking
        results = await self.search(collection_name, query_embedding, limit * 3)

        query_lower = query_text.lower()
        query_terms = set(query_lower.split())

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

            # Base keyword match boost
            keyword_matches = sum(1 for t in query_terms if t in content_lower)
            keyword_boost = keyword_matches * 0.15

            # File path match boost
            file_boost = 0.0
            for term in query_terms:
                if term in file_path:
                    file_boost += 0.25

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
                type_boost = 0.2  # File summaries are often most relevant
            elif chunk_type == "raw_file":
                type_boost = 0.2  # Raw files (configs, readme) are important
            elif chunk_type == "module":
                type_boost = 0.15  # Module-level code is often entry points
            elif chunk_type in ["function", "class"]:
                type_boost = 0.1

            # Important file boost (e.g., index, main, app files)
            important_boost = 0.0
            important_files = ["index.ts", "index.js", "main.py", "app.tsx",
                             "layout.tsx", "server.ts", "package.json", "readme.md"]
            for imp in important_files:
                if imp in file_path:
                    important_boost = 0.2
                    break

            # Calculate final score
            total_boost = keyword_boost + file_boost + pattern_boost + type_boost + important_boost
            final_score = (alpha * r.score) + ((1 - alpha) * min(total_boost, 1.0))

            boosted.append(SearchResult(
                id=r.id,
                score=final_score,
                content=r.content,
                metadata=r.metadata,
            ))

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted[:limit]

