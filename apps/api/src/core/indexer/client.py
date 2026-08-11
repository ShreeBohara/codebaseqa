"""
Async client for the Go indexer service.

Optional and off by default: the Python walk-and-parse path in IndexingService remains the
default, and this is used only when indexer_grpc_enabled is set. Both produce the same
chunk shape, so the caller does not branch beyond choosing a source.

Uses grpc.aio, which grpc documents as stable, and grpcio is already an installed
dependency (transitively via chromadb) so enabling this adds no new runtime wheel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RemoteChunk:
    """Mirrors the Chunk message. Deliberately not the ORM model: this is wire data."""
    file_path: str
    language: str
    chunk_type: str
    name: str
    content: str
    start_line: int
    end_line: int
    had_parse_error: bool


@dataclass
class IndexProgress:
    stage: str
    current_path: str
    files_processed: int
    total_files: int
    percent: float


@dataclass
class IndexSummary:
    files_walked: int
    files_parsed: int
    files_skipped: int
    chunks_emitted: int
    files_with_errors: int
    duration_ms: int


class IndexerUnavailable(RuntimeError):
    """Raised when the service cannot be reached, so the caller can fall back to Python."""


class IndexerClient:
    def __init__(self, target: str, timeout_seconds: float = 900.0):
        self._target = target
        self._timeout = timeout_seconds

    async def health(self) -> Optional[dict]:
        """Returns the service's linked grammars, or None when unreachable."""
        import grpc

        from src.core.indexer import indexer_pb2, indexer_pb2_grpc

        try:
            async with grpc.aio.insecure_channel(self._target) as channel:
                stub = indexer_pb2_grpc.IndexerStub(channel)
                res = await stub.Health(indexer_pb2.HealthRequest(), timeout=10)
                return {
                    "ok": res.ok,
                    "version": res.version,
                    # Reported rather than assumed: the Go build links a narrower grammar
                    # set than the Python parser, and pretending otherwise would silently
                    # drop languages.
                    "parsers": {p.language: list(p.extensions) for p in res.parsers},
                }
        except Exception as exc:
            logger.warning("Indexer service health check failed (%s): %s", self._target, exc)
            return None

    async def index_repo(
        self,
        repo_id: str,
        root_path: str,
        max_files: int = 0,
        max_file_size_kb: int = 0,
        batch_size: int = 0,
    ) -> AsyncIterator[object]:
        """
        Stream IndexProgress / List[RemoteChunk] / IndexSummary as the server produces them.

        Yields heterogeneous types on purpose: the caller wants progress promptly and
        chunks in batches, and forcing both into one shape would mean buffering the whole
        repository before anything is usable.
        """
        import grpc

        from src.core.indexer import indexer_pb2, indexer_pb2_grpc

        request = indexer_pb2.IndexRequest(
            repo_id=repo_id,
            root_path=root_path,
            max_files=max_files,
            max_file_size_kb=max_file_size_kb,
            batch_size=batch_size,
        )

        try:
            async with grpc.aio.insecure_channel(self._target) as channel:
                stub = indexer_pb2_grpc.IndexerStub(channel)
                async for event in stub.IndexRepo(request, timeout=self._timeout):
                    which = event.WhichOneof("event")
                    if which == "progress":
                        p = event.progress
                        yield IndexProgress(
                            stage=p.stage, current_path=p.current_path,
                            files_processed=p.files_processed, total_files=p.total_files,
                            percent=p.percent,
                        )
                    elif which == "chunks":
                        yield [
                            RemoteChunk(
                                file_path=c.file_path, language=c.language,
                                chunk_type=c.chunk_type, name=c.name, content=c.content,
                                start_line=c.start_line, end_line=c.end_line,
                                had_parse_error=c.had_parse_error,
                            )
                            for c in event.chunks.chunks
                        ]
                    elif which == "completed":
                        c = event.completed
                        yield IndexSummary(
                            files_walked=c.files_walked, files_parsed=c.files_parsed,
                            files_skipped=c.files_skipped, chunks_emitted=c.chunks_emitted,
                            files_with_errors=c.files_with_errors, duration_ms=c.duration_ms,
                        )
                    elif which == "failed":
                        # A server-side failure arrives as a stream event, not a status
                        # code, so it has to be re-raised here to stop the caller treating
                        # a truncated stream as a complete index.
                        raise IndexerUnavailable(
                            f"indexer failed: {event.failed.message} ({event.failed.path})"
                        )
        except IndexerUnavailable:
            raise
        except Exception as exc:
            raise IndexerUnavailable(f"indexer stream failed: {exc}") from exc


async def collect_chunks(client: IndexerClient, repo_id: str, root_path: str) -> List[RemoteChunk]:
    """Convenience for tests and one-shot use; drains the stream into a list."""
    out: List[RemoteChunk] = []
    async for item in client.index_repo(repo_id, root_path):
        if isinstance(item, list):
            out.extend(item)
    return out
