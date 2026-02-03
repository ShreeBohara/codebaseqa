"""
Search endpoints for semantic code search.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.dependencies import get_db, get_vector_store
from src.models.database import Repository
from src.models.schemas import ChunkType, SearchQuery, SearchResponse, SearchResult

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search_code(
    query: SearchQuery,
    db: Session = Depends(get_db),
    vector_store = Depends(get_vector_store),
):
    """Search code in a repository."""
    start_time = time.time()

    # Verify repository exists
    repo = db.query(Repository).filter(Repository.id == query.repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get query embedding
    embedding_service = vector_store._embedding_service
    query_embedding = await embedding_service.embed_query(query.query)

    # Search
    results = await vector_store.hybrid_search(
        collection_name=query.repo_id,
        query_embedding=query_embedding,
        query_text=query.query,
        limit=query.limit,
    )

    # Convert to response model
    search_results = []
    for r in results:
        # Apply filters if specified
        if query.language_filter:
            file_path = r.metadata.get("file_path", "")
            lang = r.metadata.get("language", "")
            if lang not in query.language_filter:
                continue

        if query.file_filter:
            file_path = r.metadata.get("file_path", "")
            if not any(f in file_path for f in query.file_filter):
                continue

        chunk_type_str = r.metadata.get("chunk_type", "function")
        try:
            chunk_type = ChunkType(chunk_type_str)
        except ValueError:
            chunk_type = ChunkType.FUNCTION

        search_results.append(SearchResult(
            chunk_id=r.id,
            file_path=r.metadata.get("file_path", ""),
            content=r.content,
            chunk_type=chunk_type,
            score=r.score,
            start_line=r.metadata.get("start_line", 0),
            end_line=r.metadata.get("end_line", 0),
        ))

    elapsed_ms = (time.time() - start_time) * 1000

    return SearchResponse(
        results=search_results,
        total=len(search_results),
        query_time_ms=elapsed_ms,
    )
