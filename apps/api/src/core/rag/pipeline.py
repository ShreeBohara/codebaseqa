"""
RAG Pipeline for code Q&A.
Combines retrieval and generation for answering questions about codebases.
Enhanced with query expansion, multi-query retrieval, and LLM reranking.
"""

from typing import List, Dict, Optional, AsyncGenerator, Set
from dataclasses import dataclass
import logging
import asyncio
import re

logger = logging.getLogger(__name__)


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


@dataclass
class RetrievalResult:
    """Result of retrieval phase."""
    chunks: List[RetrievedChunk]
    query: str


class RAGPipeline:
    """Enhanced RAG pipeline for code Q&A."""
    
    # Query expansion patterns
    QUERY_EXPANSIONS = {
        "entry point": ["main", "index", "app", "server", "start", "bootstrap", "init"],
        "entry": ["main", "index", "app", "start"],
        "how does": ["implementation", "function", "method", "logic"],
        "where is": ["file", "path", "location", "defined"],
        "what is": ["definition", "class", "function", "type"],
        "error": ["exception", "catch", "throw", "try", "error"],
        "api": ["route", "endpoint", "handler", "controller"],
        "database": ["model", "schema", "query", "db"],
        "auth": ["authentication", "login", "token", "session"],
    }
    
    # Improved system prompt with structured guidance
    SYSTEM_PROMPT = """You are an expert code assistant helping developers understand a codebase.

## ANSWER RULES:
1. **Start with a DIRECT answer** - First sentence should answer the question
2. **Be specific** - Name exact files, functions, line numbers
3. **Show relevant code** - Use syntax-highlighted code blocks
4. **Be concise** - No filler words, get to the point
5. **Cite sources** - Format: `filename.ts:L10-20`

## QUESTION TYPE GUIDANCE:
- **"Entry point" / "main"** → Look for: index.ts, main.py, app.tsx, server.js, package.json "main" field
- **"How does X work"** → Show the implementation, explain the flow
- **"Where is X"** → List file paths first, then show code
- **"What does X do"** → Explain purpose, show signature, key logic

## ANSWER FORMAT:
For technical questions, structure your answer as:
1. **Direct answer** (1-2 sentences)
2. **Key file(s)** with path
3. **Relevant code** (most important snippet)
4. **Brief explanation** if needed

## CODEBASE CONTEXT:
{context}

Remember: Be DIRECT and PRECISE. Developers want quick, accurate answers."""

    def __init__(self, vector_store, llm_service, repo_id: str):
        self._vector_store = vector_store
        self._llm = llm_service
        self._repo_id = repo_id
    
    def _expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms."""
        queries = [query]
        query_lower = query.lower()
        
        # Add expansions based on keywords
        for keyword, expansions in self.QUERY_EXPANSIONS.items():
            if keyword in query_lower:
                for exp in expansions[:3]:  # Limit expansions
                    expanded = f"{query} {exp}"
                    if expanded not in queries:
                        queries.append(expanded)
        
        # Add file-specific queries for common questions
        if any(term in query_lower for term in ["entry", "main", "start"]):
            queries.extend([
                "index.ts OR index.js OR main.py",
                "package.json main",
                "app.tsx layout.tsx",
            ])
        
        return queries[:5]  # Max 5 queries
    
    async def retrieve(self, query: str, limit: int = 6) -> RetrievalResult:
        """Enhanced retrieval with multi-query and deduplication."""
        embedding_service = self._vector_store._embedding_service
        
        # Expand query
        queries = self._expand_query(query)
        logger.info(f"Expanded '{query}' into {len(queries)} queries")
        
        # Retrieve for each query
        all_chunks: Dict[str, RetrievedChunk] = {}
        
        for q in queries:
            query_embedding = await embedding_service.embed_query(q)
            
            results = await self._vector_store.hybrid_search(
                collection_name=self._repo_id,
                query_embedding=query_embedding,
                query_text=q,
                limit=limit,
            )
            
            for r in results:
                chunk_id = r.id
                chunk = RetrievedChunk(
                    id=chunk_id,
                    content=r.content,
                    file_path=r.metadata.get("file_path", ""),
                    start_line=r.metadata.get("start_line", 0),
                    end_line=r.metadata.get("end_line", 0),
                    chunk_type=r.metadata.get("chunk_type", "unknown"),
                    chunk_name=r.metadata.get("chunk_name", ""),
                    score=r.score,
                )
                
                # Keep highest score for duplicates
                if chunk_id not in all_chunks or chunk.score > all_chunks[chunk_id].score:
                    all_chunks[chunk_id] = chunk
        
        # Sort by score and take top results
        chunks = sorted(all_chunks.values(), key=lambda x: x.score, reverse=True)[:limit * 2]
        
        # Apply LLM reranking for top chunks
        if len(chunks) > 5:
            chunks = await self._rerank_chunks(query, chunks)
        
        return RetrievalResult(chunks=chunks[:limit], query=query)
    
    async def _rerank_chunks(self, query: str, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Use LLM to rerank chunks by relevance."""
        try:
            # Build reranking prompt
            chunk_summaries = []
            for i, c in enumerate(chunks[:15]):  # Rerank top 15
                summary = f"{i+1}. [{c.file_path}] {c.chunk_type}: {c.chunk_name or 'unnamed'}"
                chunk_summaries.append(summary)
            
            prompt = f"""Rate the relevance of these code chunks for the question: "{query}"

Chunks:
{chr(10).join(chunk_summaries)}

Return ONLY the numbers of the top 5 most relevant chunks, comma-separated.
Example: 3,1,7,2,5"""

            messages = [{"role": "user", "content": prompt}]
            response = await self._llm.generate(messages)
            
            # Parse response
            numbers = re.findall(r'\d+', response)
            indices = [int(n) - 1 for n in numbers if n.isdigit() and 0 < int(n) <= len(chunks)]
            
            # Reorder chunks based on LLM ranking
            reranked = []
            seen = set()
            for idx in indices[:10]:
                if idx < len(chunks) and idx not in seen:
                    reranked.append(chunks[idx])
                    seen.add(idx)
            
            # Add remaining chunks not in top picks
            for i, c in enumerate(chunks):
                if i not in seen:
                    reranked.append(c)
            
            logger.info(f"Reranked {len(chunks)} chunks, top pick: {reranked[0].file_path if reranked else 'none'}")
            return reranked
            
        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return chunks
    
    def _build_context(self, chunks: List[RetrievedChunk], max_chars: int = 15000) -> str:
        """Build structured context grouped by file with size limits."""
        if not chunks:
            return "No relevant code found."
        
        # Group by file
        by_file: Dict[str, List[RetrievedChunk]] = {}
        for c in chunks:
            by_file.setdefault(c.file_path, []).append(c)
        
        # Build hierarchical context with size tracking
        parts = []
        total_chars = 0
        
        # Add file overview first
        parts.append("### Files Referenced:")
        for file_path in by_file.keys():
            parts.append(f"- `{file_path}`")
        parts.append("")
        
        # Add code by file, respecting size limit
        for file_path, file_chunks in by_file.items():
            if total_chars > max_chars:
                parts.append(f"\n*[Context truncated - {len(by_file) - len(parts)} more files...]*")
                break
                
            parts.append(f"### {file_path}")
            
            for c in file_chunks:
                # Truncate individual chunks to max 1500 chars
                content = c.content.strip()
                if len(content) > 1500:
                    content = content[:1500] + "\n... [truncated]"
                
                type_label = c.chunk_type.upper()
                name_label = f" `{c.chunk_name}`" if c.chunk_name else ""
                parts.append(f"**{type_label}**{name_label} (L{c.start_line}-{c.end_line}):")
                
                # Determine language for syntax highlighting
                lang = "typescript" if file_path.endswith(('.ts', '.tsx')) else \
                       "python" if file_path.endswith('.py') else \
                       "javascript" if file_path.endswith(('.js', '.jsx')) else \
                       "json" if file_path.endswith('.json') else \
                       "yaml" if file_path.endswith(('.yml', '.yaml')) else \
                       "markdown" if file_path.endswith('.md') else ""
                
                chunk_text = f"```{lang}\n{content}\n```\n"
                total_chars += len(chunk_text)
                parts.append(chunk_text)
        
        return "\n".join(parts)
    
    async def generate(
        self,
        query: str,
        context: RetrievalResult,
        history: List[Dict] = None,
    ) -> str:
        """Generate a response (non-streaming)."""
        context_str = self._build_context(context.chunks)
        system = self.SYSTEM_PROMPT.format(context=context_str)
        
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})
        
        return await self._llm.generate(messages)
    
    async def generate_stream(
        self,
        query: str,
        context: RetrievalResult,
        history: List[Dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        context_str = self._build_context(context.chunks)
        system = self.SYSTEM_PROMPT.format(context=context_str)
        
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})
        
        async for token in self._llm.generate_stream(messages):
            yield token

