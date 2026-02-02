"""
Repository indexing service.
Handles cloning, parsing, and embedding of code repositories.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import Session

from src.config import settings
from src.models.database import Repository, CodeFile, CodeChunk, IndexingStatus
from src.core.github.repo_manager import RepoManager
from src.core.parser.tree_sitter_parser import get_parser_for_file
from src.dependencies import get_vector_store, get_embedding_service

logger = logging.getLogger(__name__)

# File extensions to index
INDEXED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rs", ".c", ".cpp", ".h",
    ".rb", ".php", ".swift", ".kt",
    ".md", ".json",  # Add README and config files
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
            # Update status to cloning
            repo.status = IndexingStatus.CLONING
            self._db.commit()
            self._update_progress(repo_id, "cloning", "Cloning repository...", 0)
            
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
            self._update_progress(repo_id, "parsing", "Parsing code files...", 20)
            
            # Find and parse files
            files = self._find_files(local_path)
            total_files = len(files)
            logger.info(f"Found {total_files} files to index")
            
            chunks_data = []
            for i, file_path in enumerate(files):
                progress_pct = 20 + (60 * (i / max(total_files, 1)))
                self._update_progress(repo_id, "parsing", f"Parsing {file_path.name}...", progress_pct)
                
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
            self._update_progress(repo_id, "embedding", "Generating embeddings...", 80)
            
            # Generate embeddings and store
            if chunks_data:
                await self._embed_and_store(repo_id, chunks_data)
            
            # Complete
            repo.status = IndexingStatus.COMPLETED
            repo.last_indexed_at = datetime.utcnow()
            self._db.commit()
            self._update_progress(repo_id, "completed", "Indexing complete!", 100)
            
            logger.info(f"Successfully indexed {repo.github_owner}/{repo.github_name}")
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            repo.status = IndexingStatus.FAILED
            repo.indexing_error = str(e)
            self._db.commit()
            self._update_progress(repo_id, "failed", str(e), 0)
    
    def _find_files(self, repo_path: Path) -> List[Path]:
        """Find all indexable files in repository."""
        files = []
        
        for root, dirs, filenames in os.walk(repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS]
            
            for filename in filenames:
                file_path = Path(root) / filename
                
                # Check extension
                if file_path.suffix.lower() not in INDEXED_EXTENSIONS:
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
        lang_map = {'.json': 'json', '.md': 'markdown', '.yml': 'yaml', '.yaml': 'yaml'}
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
        
        # For important files, index the whole content (truncated if needed)
        is_important = file_path.name.lower() in IMPORTANT_FILES
        max_content_len = 5000 if is_important else 3000
        
        chunk_content = content[:max_content_len]
        if len(content) > max_content_len:
            chunk_content += "\n... [truncated]"
        
        # Create single chunk for entire file
        db_chunk = CodeChunk(
            repository_id=repo.id,
            file_id=db_file.id,
            chunk_type="raw_file" if not is_important else "file_summary",
            chunk_name=file_path.name,
            content=chunk_content,
            content_hash=hashlib.sha256(chunk_content.encode()).hexdigest(),
            start_line=1,
            end_line=min(line_count, 200),
            docstring=f"Raw content of {file_path.name}",
            context_before="",
        )
        self._db.add(db_chunk)
        self._db.commit()
        self._db.refresh(db_chunk)
        
        chunks_data.append({
            "id": db_chunk.id,
            "content": f"FILE: {file_path.name}\n{chunk_content}",
            "metadata": {
                "file_path": relative_path,
                "chunk_type": db_chunk.chunk_type,
                "chunk_name": file_path.name,
                "start_line": 1,
                "end_line": min(line_count, 200),
                "language": language,
                "is_important": is_important,
            },
        })
        
        logger.info(f"Indexed raw file: {file_path.name} ({len(chunk_content)} chars)")
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
        
        result = parser.parse(content, str(file_path))
        
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
    
    def _update_progress(self, repo_id: str, status: str, step: str, percent: float):
        """Update progress tracking."""
        self._progress[repo_id] = {
            "status": status,
            "current_step": step,
            "progress_percent": percent,
        }
    
    async def get_progress(self, repo_id: str) -> Dict[str, Any]:
        """Get current progress for a repository."""
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
