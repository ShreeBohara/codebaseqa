"""
Repository indexing service.
Handles cloning, parsing, and embedding of code repositories.
"""

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.config import settings
from src.core.github.repo_manager import RepoManager
from src.core.parser.tree_sitter_parser import get_parser_for_file
from src.dependencies import get_embedding_service, get_vector_store
from src.models.database import (
    CodeChunk,
    CodeDependency,
    CodeFile,
    IndexingStatus,
    Repository,
)

logger = logging.getLogger(__name__)

# File extensions to index
INDEXED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".ipp", ".tpp",
    ".cs", ".csx",
    ".rb", ".rake", ".gemspec", ".php", ".swift", ".kt",
    ".erb",
    ".md", ".json",  # Add README and config files
}

# Extensionless (or special-name) files to index for Rails basics.
INDEXED_FILENAMES = {
    "gemfile", "rakefile", "config.ru",
}

# Important files that get special treatment (file-level summary chunk)
IMPORTANT_FILES = {
    "readme.md", "readme", "package.json", "pyproject.toml",
    "index.ts", "index.js", "index.tsx", "main.py", "main.ts",
    "app.tsx", "app.ts", "app.js", "layout.tsx", "layout.ts",
    "server.ts", "server.js", "config.ts", "config.js",
    "next.config.ts", "next.config.js", "vite.config.ts",
}

# Files and directories to skip
SKIP_PATTERNS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    "dist", "build", ".next", "coverage", ".pytest_cache",
    "vendor", "target", ".idea", ".vscode",
}


class IndexingService:
    """Service for indexing repositories."""

    def __init__(self, db: Session):
        self._db = db
        self._repo_manager = RepoManager()
        self._progress: Dict[str, Dict[str, Any]] = {}

    async def index_repository(self, repo_id: str, force_reindex: bool = False):
        """Index a repository."""
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found")
            return

        try:
            # Always rebuild the index snapshot from scratch to prevent stale/duplicate chunks.
            await self._reset_repository_index_data(repo_id)

            # Update status to cloning
            repo.status = IndexingStatus.CLONING
            self._db.commit()
            await self._publish_progress(repo_id, "cloning", "Cloning repository...", 0)

            # Clone repository
            local_path = await self._repo_manager.clone_repository(
                repo.github_url,
                repo.github_owner,
                repo.github_name,
                repo.default_branch,
            )
            repo.local_path = str(local_path)
            repo.last_commit_sha = await self._repo_manager.get_current_commit(local_path)
            self._db.commit()

            # Update status to parsing
            repo.status = IndexingStatus.PARSING
            self._db.commit()
            await self._publish_progress(repo_id, "parsing", "Parsing code files...", 20)

            # Find and parse files
            files = self._find_files(local_path)
            total_files = len(files)
            logger.info(f"Found {total_files} files to index")

            chunks_data = []
            for i, file_path in enumerate(files):
                progress_pct = 20 + (60 * (i / max(total_files, 1)))
                await self._publish_progress(repo_id, "parsing", f"Parsing {file_path.name}...", progress_pct, i, total_files)

                try:
                    file_chunks = await self._parse_file(repo, file_path, local_path)
                    chunks_data.extend(file_chunks)
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

            repo.total_files = total_files
            repo.total_chunks = len(chunks_data)
            self._db.commit()

            # Update status to embedding
            repo.status = IndexingStatus.EMBEDDING
            self._db.commit()
            await self._publish_progress(repo_id, "embedding", "Generating embeddings...", 80)

            # Generate embeddings and store
            if chunks_data:
                await self._embed_and_store(repo_id, chunks_data)

            # Derive the dependency graph while the clone is still on disk.
            #
            # This used to happen inside every graph request instead, which meant
            # reading every source file off disk on the event loop behind a 45-second
            # cache, and it silently produced a worse graph once the clone was gone
            # (after a redeploy or container restart) because it fell back to the
            # unresolved import strings on CodeFile. Doing it here is the only point
            # where the working tree is guaranteed to exist.
            #
            # Deliberately non-fatal: a graph derivation failure must not fail an
            # otherwise good index, and the read path can still fall back.
            try:
                await self._persist_dependency_graph(repo)
            except Exception as exc:
                logger.warning(
                    "Dependency graph derivation failed for %s; the graph endpoint will "
                    "fall back to deriving on request: %s",
                    repo_id, exc,
                )

            # Complete
            repo.status = IndexingStatus.COMPLETED
            repo.last_indexed_at = datetime.now(timezone.utc)
            self._db.commit()
            await self._publish_progress(repo_id, "completed", "Indexing complete!", 100, total_files, total_files)

            logger.info(f"Successfully indexed {repo.github_owner}/{repo.github_name}")

        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            repo.status = IndexingStatus.FAILED
            repo.indexing_error = str(e)
            self._db.commit()
            await self._publish_progress(repo_id, "failed", str(e), 0)

    async def _reset_repository_index_data(self, repo_id: str) -> None:
        """Clear prior SQL/vector artifacts for a repository before full re-index."""
        self._db.query(CodeChunk).filter(CodeChunk.repository_id == repo_id).delete(synchronize_session=False)
        self._db.query(CodeFile).filter(CodeFile.repository_id == repo_id).delete(synchronize_session=False)
        # Stale edges would otherwise union with the newly derived ones, since the
        # uniqueness constraint is on (repo, source, target, relation) and a renamed or
        # deleted file produces edges that no longer have a counterpart.
        self._db.query(CodeDependency).filter(
            CodeDependency.repository_id == repo_id
        ).delete(synchronize_session=False)
        self._db.commit()

        try:
            vector_store = get_vector_store()
            await vector_store.delete_collection(repo_id)
        except Exception as exc:
            logger.warning("Failed to clear existing vector collection for repo %s: %s", repo_id, exc)

    async def _persist_dependency_graph(self, repo: Repository) -> int:
        """
        Derive import edges once and store them in code_dependencies.

        Reuses LearningService's resolution logic rather than reimplementing it, so
        there is exactly one definition of what an edge is and how it is classified.
        The file reading is offloaded to a worker thread because it is blocking and
        proportional to repository size -- this runs inside the indexing task, which
        shares an event loop with nothing, but keeping it off the loop means the same
        method is safe to call from a request handler later if that is ever wanted.
        """
        from src.services.learning_service import LearningService

        files = self._db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
        if not files:
            return 0

        service = LearningService(self._db, llm=None, vector_store=None)
        file_map = {f.path: f for f in files}
        all_paths = set(file_map)
        source_paths = sorted(all_paths)

        edges = await asyncio.to_thread(
            service._build_deterministic_edges, repo, source_paths, all_paths, file_map
        )

        rows = [
            CodeDependency(
                repository_id=repo.id,
                source_path=edge.source,
                target_path=edge.target,
                relation=getattr(edge, "relation", None) or "imports",
                weight=int(getattr(edge, "weight", 1) or 1),
                confidence=float(getattr(edge, "confidence", 0.72) or 0.72),
            )
            for edge in edges
        ]

        if rows:
            self._db.bulk_save_objects(rows)
        self._db.commit()

        logger.info(
            "Derived %d dependency edges for %s/%s at index time",
            len(rows), repo.github_owner, repo.github_name,
        )

        # Project into the Neo4j read model if it is enabled. SQL stays authoritative,
        # so a failure here is logged and ignored -- the graph endpoint falls back.
        await self._sync_graph_store(repo, files, rows)

        return len(rows)

    async def _sync_graph_store(self, repo, files, edge_rows) -> None:
        """Mirror the freshly derived graph into Neo4j. Never raises."""
        from src.dependencies import get_graph_store

        store = get_graph_store()
        if store is None:
            return

        try:
            from src.services.learning_service import LearningService
            service = LearningService(self._db, llm=None, vector_store=None)

            file_payload = [
                {
                    "path": f.path,
                    "filename": f.filename,
                    "extension": f.extension,
                    "language": f.language,
                    "loc": f.line_count or 0,
                    "module_key": service._module_key_for_path(f.path),
                }
                for f in files
            ]
            edge_payload = [
                {
                    "source": r.source_path,
                    "target": r.target_path,
                    "relation": r.relation or "imports",
                    "weight": r.weight or 1,
                    "confidence": r.confidence if r.confidence is not None else 0.72,
                }
                for r in edge_rows
            ]
            await store.sync_repository(repo.id, file_payload, edge_payload)
        except Exception as exc:
            logger.warning(
                "Neo4j graph sync failed for %s (SQL graph is unaffected): %s", repo.id, exc
            )

    def _find_files(self, repo_path: Path) -> List[Path]:
        """Find all indexable files in repository."""
        files = []

        for root, dirs, filenames in os.walk(repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS]

            for filename in filenames:
                file_path = Path(root) / filename

                # Check extension
                suffix = file_path.suffix.lower()
                filename_lower = file_path.name.lower()
                if suffix not in INDEXED_EXTENSIONS and filename_lower not in INDEXED_FILENAMES:
                    continue

                # Check file size
                try:
                    size_kb = file_path.stat().st_size / 1024
                    if size_kb > settings.max_file_size_kb:
                        continue
                except OSError:
                    continue

                files.append(file_path)

                # Limit total files
                if len(files) >= settings.max_files_per_repo:
                    break

        return files

    def _is_trivial_reexport(self, content: str) -> bool:
        compact = re.sub(r"\s+", " ", content.strip().lower())
        if compact in {"export {};", "export {}"}:
            return True
        if len(compact) <= 64 and compact.startswith("export"):
            return True
        return False

    def _chunk_markdown_by_headings(self, content: str, max_chunk_len: int = 2200) -> List[Dict[str, Any]]:
        """Chunk markdown content by heading boundaries with size caps."""
        lines = content.splitlines()
        if not lines:
            return []

        sections: List[Dict[str, Any]] = []
        current_title = "Document"
        current_start = 1
        current_lines: List[str] = []

        for line_no, line in enumerate(lines, start=1):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match and current_lines:
                section_content = "\n".join(current_lines).strip()
                if section_content:
                    sections.append(
                        {
                            "title": current_title,
                            "start_line": current_start,
                            "end_line": line_no - 1,
                            "content": section_content,
                        }
                    )
                current_title = heading_match.group(2).strip()
                current_start = line_no
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            section_content = "\n".join(current_lines).strip()
            if section_content:
                sections.append(
                    {
                        "title": current_title,
                        "start_line": current_start,
                        "end_line": len(lines),
                        "content": section_content,
                    }
                )

        if not sections:
            return []

        chunked: List[Dict[str, Any]] = []
        for section in sections:
            section_lines = section["content"].splitlines()
            line_cursor = section["start_line"]
            buffer: List[str] = []

            for raw_line in section_lines:
                prospective = "\n".join(buffer + [raw_line]).strip()
                if buffer and len(prospective) > max_chunk_len:
                    chunk_content = "\n".join(buffer).strip()
                    if chunk_content:
                        chunked.append(
                            {
                                "title": section["title"],
                                "start_line": line_cursor,
                                "end_line": line_cursor + max(0, len(buffer) - 1),
                                "content": chunk_content,
                            }
                        )
                    line_cursor += len(buffer)
                    buffer = [raw_line]
                else:
                    buffer.append(raw_line)

            if buffer:
                chunk_content = "\n".join(buffer).strip()
                if chunk_content:
                    chunked.append(
                        {
                            "title": section["title"],
                            "start_line": line_cursor,
                            "end_line": line_cursor + max(0, len(buffer) - 1),
                            "content": chunk_content,
                        }
                    )

        return chunked

    async def _index_raw_file(
        self,
        repo: Repository,
        file_path: Path,
        repo_path: Path,
        content: str
    ) -> List[Dict[str, Any]]:
        """Index files without parsers (JSON, MD) as raw content chunks."""
        relative_path = str(file_path.relative_to(repo_path))
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        line_count = content.count('\n') + 1

        # Determine language
        lang_map = {
            '.json': 'json',
            '.md': 'markdown',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.erb': 'erb',
            '.rb': 'ruby',
            '.rake': 'ruby',
            '.gemspec': 'ruby',
            '.ru': 'ruby',
        }
        filename_lower = file_path.name.lower()
        if filename_lower in {"gemfile", "rakefile"}:
            language = "ruby"
        else:
            language = lang_map.get(file_path.suffix.lower(), 'text')

        # Create CodeFile record
        db_file = CodeFile(
            repository_id=repo.id,
            path=relative_path,
            filename=file_path.name,
            extension=file_path.suffix,
            language=language,
            size_bytes=len(content.encode()),
            line_count=line_count,
            content_hash=content_hash,
            imports=[],
        )
        self._db.add(db_file)
        self._db.commit()
        self._db.refresh(db_file)

        chunks_data = []
        is_important = file_path.name.lower() in IMPORTANT_FILES
        chunk_specs: List[Dict[str, Any]] = []

        if language == "markdown" and len(content) > 2200:
            md_chunks = self._chunk_markdown_by_headings(content, max_chunk_len=2200 if is_important else 1800)
            for idx, md_chunk in enumerate(md_chunks):
                chunk_type = "file_summary" if is_important and idx == 0 else "raw_file"
                chunk_specs.append(
                    {
                        "chunk_type": chunk_type,
                        "chunk_name": md_chunk["title"] or file_path.name,
                        "content": md_chunk["content"],
                        "start_line": md_chunk["start_line"],
                        "end_line": md_chunk["end_line"],
                    }
                )
        else:
            max_content_len = 5000 if is_important else 3000
            chunk_content = content[:max_content_len]
            if len(content) > max_content_len:
                chunk_content += "\n... [truncated]"
            chunk_specs.append(
                {
                    "chunk_type": "file_summary" if is_important else "raw_file",
                    "chunk_name": file_path.name,
                    "content": chunk_content,
                    "start_line": 1,
                    "end_line": min(line_count, 200),
                }
            )

        db_chunks = []
        for spec in chunk_specs:
            db_chunk = CodeChunk(
                repository_id=repo.id,
                file_id=db_file.id,
                chunk_type=spec["chunk_type"],
                chunk_name=spec["chunk_name"],
                content=spec["content"],
                content_hash=hashlib.sha256(spec["content"].encode()).hexdigest(),
                start_line=spec["start_line"],
                end_line=spec["end_line"],
                docstring=f"Raw content of {file_path.name}",
                context_before="",
            )
            db_chunks.append(db_chunk)

        if db_chunks:
            self._db.add_all(db_chunks)
            self._db.commit()

        for db_chunk in db_chunks:
            self._db.refresh(db_chunk)
            chunks_data.append(
                {
                    "id": db_chunk.id,
                    "content": f"FILE: {file_path.name}\n{db_chunk.content}",
                    "metadata": {
                        "file_path": relative_path,
                        "chunk_type": db_chunk.chunk_type,
                        "chunk_name": db_chunk.chunk_name or file_path.name,
                        "start_line": db_chunk.start_line,
                        "end_line": db_chunk.end_line,
                        "language": language,
                        "is_important": is_important,
                    },
                }
            )

        logger.info("Indexed raw file: %s (%s chunks)", file_path.name, len(chunks_data))
        return chunks_data

    async def _parse_file(
        self,
        repo: Repository,
        file_path: Path,
        repo_path: Path
    ) -> List[Dict[str, Any]]:
        """Parse a single file and return chunk data."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []

        parser = get_parser_for_file(str(file_path))

        # Fallback for files without parsers (JSON, MD, etc.)
        if not parser:
            return await self._index_raw_file(repo, file_path, repo_path, content)

        try:
            result = parser.parse(content, str(file_path))
        except Exception as exc:
            logger.warning("Parser failed for %s, falling back to raw indexing: %s", file_path, exc)
            return await self._index_raw_file(repo, file_path, repo_path, content)

        # tree-sitter returns an ERROR-node tree rather than raising when it cannot
        # parse the file, so the except above never fires for a grammar mismatch.
        # Chunks carved out of an ERROR tree have wrong boundaries -- raw indexing
        # is strictly better than mis-aligned AST chunks.
        if result.has_errors:
            logger.warning(
                "Parser produced an ERROR tree for %s (language=%s); falling back to raw indexing",
                file_path,
                result.language,
            )
            return await self._index_raw_file(repo, file_path, repo_path, content)

        # Create CodeFile record
        relative_path = str(file_path.relative_to(repo_path))
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        db_file = CodeFile(
            repository_id=repo.id,
            path=relative_path,
            filename=file_path.name,
            extension=file_path.suffix,
            language=result.language,
            size_bytes=len(content.encode()),
            line_count=result.line_count,
            content_hash=content_hash,
            imports=result.imports,
        )
        self._db.add(db_file)
        self._db.commit()
        self._db.refresh(db_file)

        # Create chunks - batch for performance
        chunks_data = []
        db_chunks = []

        # Add file summary chunk for important files
        is_important = file_path.name.lower() in IMPORTANT_FILES
        if is_important:
            # Create a file summary chunk (first 3000 chars or whole file)
            summary_content = content[:3000]
            if len(content) > 3000:
                summary_content += "\n... [truncated]"

            if not self._is_trivial_reexport(summary_content):
                summary_chunk = CodeChunk(
                    repository_id=repo.id,
                    file_id=db_file.id,
                    chunk_type="file_summary",
                    chunk_name=file_path.name,
                    content=summary_content,
                    content_hash=hashlib.sha256(summary_content.encode()).hexdigest(),
                    start_line=1,
                    end_line=min(result.line_count, 100),
                    docstring=f"File summary: {file_path.name}",
                    context_before="",
                )
                db_chunks.append(summary_chunk)

                chunks_data.append({
                    "chunk": summary_chunk,
                    "content": f"FILE: {file_path.name}\n{summary_content}",
                    "metadata": {
                        "file_path": relative_path,
                        "chunk_type": "file_summary",
                        "chunk_name": file_path.name,
                        "start_line": 1,
                        "end_line": min(result.line_count, 100),
                        "language": result.language,
                        "is_important": True,
                    },
                })
                logger.info(f"Created file summary chunk for important file: {file_path.name}")
            else:
                logger.info("Skipped trivial file summary for %s", file_path.name)

        for chunk in result.chunks:
            chunk_hash = hashlib.sha256(chunk.content.encode()).hexdigest()

            db_chunk = CodeChunk(
                repository_id=repo.id,
                file_id=db_file.id,
                chunk_type=chunk.chunk_type.value,
                chunk_name=chunk.name,
                content=chunk.content,
                content_hash=chunk_hash,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                docstring=chunk.docstring,
                context_before=chunk.context_before,
            )
            db_chunks.append(db_chunk)

            # Build metadata, filtering out None values (ChromaDB doesn't accept None)
            metadata = {
                "file_path": relative_path,
                "chunk_type": chunk.chunk_type.value,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "language": result.language,
            }
            # Only add chunk_name if it's not None
            if chunk.name:
                metadata["chunk_name"] = chunk.name

            chunks_data.append({
                "chunk": db_chunk,
                "content": chunk.content,
                "metadata": metadata,
            })

        # Batch commit all chunks at once (10x faster than individual commits)
        if db_chunks:
            self._db.add_all(db_chunks)
            self._db.commit()

            # Refresh and update IDs
            for item in chunks_data:
                self._db.refresh(item["chunk"])
                item["id"] = item["chunk"].id
                del item["chunk"]

        return chunks_data

    async def _embed_and_store(self, repo_id: str, chunks_data: List[Dict[str, Any]]):
        """Generate embeddings and store in vector database."""
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()

        # Create collection
        await vector_store.create_collection(repo_id, embedding_service.dimensions)

        # Batch embed
        texts = [c["content"] for c in chunks_data]
        embeddings = await embedding_service.embed_texts(texts)

        # Store
        await vector_store.add_documents(
            collection_name=repo_id,
            ids=[c["id"] for c in chunks_data],
            embeddings=embeddings,
            documents=texts,
            metadatas=[c["metadata"] for c in chunks_data],
        )

    async def _publish_progress(
        self, repo_id: str, status: str, step: str, percent: float,
        files_processed: int = 0, total_files: int = 0,
    ) -> None:
        """
        Record progress where a *different* process can read it.

        _update_progress below writes an instance dict, which the SSE endpoint can never
        see because it builds its own IndexingService. This is the write that actually
        reaches a client.
        """
        self._update_progress(repo_id, status, step, percent)
        try:
            from src.dependencies import get_progress_store

            await get_progress_store().publish(
                repo_id, status, step, percent, files_processed, total_files
            )
        except Exception as exc:
            logger.debug("Progress publish failed for %s: %s", repo_id, exc)

    def _update_progress(self, repo_id: str, status: str, step: str, percent: float):
        """Update progress tracking."""
        self._progress[repo_id] = {
            "status": status,
            "current_step": step,
            "progress_percent": percent,
        }

    async def get_progress(self, repo_id: str) -> Dict[str, Any]:
        """
        Current progress for a repository.

        Order matters: the shared store first, because it is the only source a *different*
        process (the SSE request handler) can observe. The instance dict and the database
        fallback follow for the single-process case and for repos with no live indexer.
        """
        try:
            from src.dependencies import get_progress_store

            event = await get_progress_store().latest(repo_id)
            if event:
                return {
                    "repo_id": repo_id,
                    "status": event.get("status", "unknown"),
                    "current_step": event.get("current_step", ""),
                    "progress_percent": event.get("progress_percent", 0),
                    "files_processed": event.get("files_processed", 0),
                    "total_files": event.get("total_files", 0),
                }
        except Exception as exc:
            logger.debug("Progress store read failed for %s: %s", repo_id, exc)

        if repo_id in self._progress:
            return {
                "repo_id": repo_id,
                **self._progress[repo_id],
                "files_processed": 0,
                "total_files": 0,
            }

        # Fallback to database status
        repo = self._db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            return {
                "repo_id": repo_id,
                "status": repo.status.value,
                "current_step": "Unknown",
                "progress_percent": 100 if repo.status == IndexingStatus.COMPLETED else 0,
                "files_processed": repo.total_files,
                "total_files": repo.total_files,
                "error": repo.indexing_error,
            }

        return {"repo_id": repo_id, "status": "unknown", "progress_percent": 0}
