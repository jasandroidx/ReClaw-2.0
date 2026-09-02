"""
Vault Sync — Obsidian Vault Synchronization for RAG.

Watches the configured Obsidian vault for markdown files,
auto-ingests them into the vector store for semantic search.

Features:
  - Full vault scan (initial or periodic)
  - File watcher for real-time sync (optional)
  - Deduplication via checksum (re-ingest only changed files)
  - Respects .gitignore patterns
  - Skips templates, daily notes, and meta files
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from .ingestor import DocumentIngestor
from .models import VaultSyncStatus
from .vectorstore import VectorStore


class VaultSynchronizer:
    """
    Synchronize Obsidian vault with the RAG knowledge base.

    Usage:
        sync = VaultSynchronizer(vault_path="/root/obsidian_vault")
        status = sync.full_sync()  # Scan and ingest all files
        # or
        sync.watch_for_changes()   # Start watching (blocking)
    """

    # Files/folders to skip
    SKIP_PATTERNS = [
        "**/harvest/dry-run/**",
        "**/sessions/**",
        "**/handoffs/**",
        "**/_archives/**",
        "**/.obsidian/**",
        ".git/",
        ".obsidian/",
        "templates/",
        "Templates/",
        "node_modules/",
        "_templates/",
        "Daily/",
        "daily/",
        "*.tmp",
        "*.bak",
        ".trash/",
        "_archive/",
        "__pycache__/",
        "library/processed/",
    ]

    # Automatic full vault sync: distilled notes only.
    # Raw PDFs/CSV/TXT still go in when Jason names a file and we POST /rag/ingest.
    INGEST_EXTENSIONS = {".md", ".markdown"}

    HIDDEN_STATUSES = frozenset({"superseded", "trash", "skip", "retired"})

    # State file for tracking what's been ingested
    STATE_FILENAME = "vault_sync_state.json"

    def __init__(
        self,
        vault_path: str | Path,
        ingestor: DocumentIngestor | None = None,
        vector_store: VectorStore | None = None,
        state_dir: str | Path = "data/rag_state",
        on_sync: Callable | None = None,
    ):
        self.vault_path = Path(vault_path)
        self.ingestor = ingestor or DocumentIngestor()
        self.vector_store = vector_store or VectorStore()
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / self.STATE_FILENAME
        self.on_sync = on_sync  # callback after sync
        self._state: dict[str, dict] = {}  # path -> {checksum, doc_id, synced_at}
        self._is_watching = False
        self._load_state()

    @property
    def is_watching(self) -> bool:
        return self._is_watching

    def full_sync(
        self,
        force_reingest: bool = False,
    ) -> VaultSyncStatus:
        """
        Perform a full scan and sync of the vault.

        Args:
            force_reingest: Re-ingest all files even if unchanged

        Returns:
            VaultSyncStatus with results
        """
        if not self.vault_path.exists():
            return VaultSyncStatus(
                vault_path=str(self.vault_path),
                total_documents=0,
                total_chunks=0,
                errors=[f"Vault path does not exist: {self.vault_path}"],
            )

        files = self._discover_files()
        errors: list[str] = []
        ingested_count = 0
        skipped_count = 0
        new_state: dict[str, dict] = {}

        for file_path in files:
            rel_path = str(file_path.relative_to(self.vault_path))
            if self._peek_note_status(file_path) in self.HIDDEN_STATUSES:
                existing = self._state.get(rel_path)
                if existing and existing.get("doc_id"):
                    try:
                        self.vector_store.delete_document(existing["doc_id"])
                    except Exception:
                        pass
                skipped_count += 1
                continue

            checksum = self._file_checksum(file_path)

            # Check if already ingested and unchanged
            existing = self._state.get(rel_path)
            if not force_reingest and existing and existing.get("checksum") == checksum:
                new_state[rel_path] = existing
                skipped_count += 1
                continue

            # Delete old chunks if re-ingesting
            if existing and existing.get("doc_id"):
                try:
                    self.vector_store.delete_document(existing["doc_id"])
                except Exception:
                    pass

            # Ingest
            try:
                result = self.ingestor.ingest_file(
                    file_path=file_path,
                    source_type="obsidian",
                    vault_path=str(self.vault_path),
                )
                if result.error:
                    errors.append(f"{rel_path}: {result.error}")
                else:
                    ingested_count += 1
                    new_state[rel_path] = {
                        "checksum": checksum,
                        "doc_id": result.document_id,
                        "synced_at": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as e:
                errors.append(f"{rel_path}: {e}")

        # Clean up removed files
        removed = set(self._state.keys()) - set(new_state.keys())
        for rel_path in removed:
            old_doc_id = self._state[rel_path].get("doc_id")
            if old_doc_id:
                try:
                    self.vector_store.delete_document(old_doc_id)
                except Exception:
                    pass

        self._state = new_state
        self._save_state()

        total_docs = len(new_state)
        total_chunks = self.vector_store.count()

        if self.on_sync:
            self.on_sync(total_docs, total_chunks)

        return VaultSyncStatus(
            vault_path=str(self.vault_path),
            last_sync=datetime.now(timezone.utc),
            total_documents=total_docs,
            total_chunks=total_chunks,
            is_watching=self._is_watching,
            errors=errors[:10],  # Limit errors
        )

    def watch_for_changes(self, interval_seconds: int = 30) -> None:
        """
        Watch vault for changes and sync periodically.
        This is a blocking loop — run in a background thread.

        Args:
            interval_seconds: Seconds between scans
        """
        self._is_watching = True
        try:
            while self._is_watching:
                self.full_sync()
                time.sleep(interval_seconds)
        finally:
            self._is_watching = False

    def stop_watching(self) -> None:
        """Stop the watch loop."""
        self._is_watching = False

    def _discover_files(self) -> list[Path]:
        """Discover all ingestable files in the vault."""
        files: list[Path] = []
        for path in self.vault_path.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.vault_path))
            # Skip patterns
            if any(
                fnmatch.fnmatch(rel, pattern) or pattern in rel
                for pattern in self.SKIP_PATTERNS
            ):
                continue
            # Check extension
            if path.suffix.lower() not in self.INGEST_EXTENSIONS:
                continue
            files.append(path)
        return sorted(files)

    def _peek_note_status(self, file_path: Path) -> str:
        """Frontmatter status only. Missing/invalid → empty (indexable)."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            return ""
        if not text.startswith("---"):
            return ""
        end = text.find("\n---", 3)
        if end < 0:
            return ""
        try:
            fm = yaml.safe_load(text[4:end]) or {}
        except yaml.YAMLError:
            return ""
        if not isinstance(fm, dict):
            return ""
        return str(fm.get("status") or "").strip().lower()

    def _file_checksum(self, file_path: Path) -> str:
        """Quick checksum for file content."""
        h = hashlib.md5()
        try:
            h.update(file_path.read_bytes())
        except Exception:
            h.update(str(file_path.stat().st_mtime).encode())
        return h.hexdigest()

    def _load_state(self) -> None:
        """Load sync state from disk."""
        if self.state_file.exists():
            try:
                self._state = json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, KeyError):
                self._state = {}

    def _save_state(self) -> None:
        """Save sync state to disk."""
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def get_status(self) -> VaultSyncStatus:
        """Get current sync status without running sync."""
        return VaultSyncStatus(
            vault_path=str(self.vault_path),
            last_sync=self._state.get("_last_sync"),
            total_documents=len(self._state),
            total_chunks=self.vector_store.count(),
            is_watching=self._is_watching,
        )
