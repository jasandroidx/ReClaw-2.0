"""
Tests for vault synchronization.
"""

import tempfile
from pathlib import Path

import pytest

from rag.vault_sync import VaultSynchronizer
from rag.vectorstore import VectorStore
from rag.ingestor import DocumentIngestor
from rag.embeddings import EmbeddingManager


class TestVaultSynchronizer:
    def test_discover_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            # Create test files
            (vault / "note1.md").write_text("# Note 1\n\nContent here.")
            (vault / "subdir").mkdir()
            (vault / "subdir" / "note2.md").write_text("# Note 2\n\nMore content.")
            # Create file that should be skipped
            (vault / ".obsidian").mkdir()
            (vault / ".obsidian" / "config").write_text("obsidian config")

            sync = VaultSynchronizer(
                vault_path=vault,
                state_dir=Path(tmpdir) / "state",
            )
            files = sync._discover_files()
            paths = [f.name for f in files]
            assert "note1.md" in paths
            assert "note2.md" in paths
            assert "config" not in paths

    def test_file_checksum(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("test content")
            f.flush()

            sync = VaultSynchronizer(
                vault_path="/tmp",
                state_dir=Path(tempfile.gettempdir()),
            )
            cs1 = sync._file_checksum(Path(f.name))
            cs2 = sync._file_checksum(Path(f.name))
            assert cs1 == cs2
            assert len(cs1) == 32  # MD5 hex
            Path(f.name).unlink()

    def test_skip_patterns(self):
        sync = VaultSynchronizer(
            vault_path="/tmp",
            state_dir=Path(tempfile.gettempdir()),
        )
        # Files in .obsidian should be skipped
        assert any(".obsidian/" in p for p in sync.SKIP_PATTERNS)
        assert any("templates/" in p for p in sync.SKIP_PATTERNS)
        assert ".pdf" not in sync.INGEST_EXTENSIONS
        assert ".md" in sync.INGEST_EXTENSIONS

    def test_peek_note_status_and_hidden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            live = vault / "live.md"
            dead = vault / "dead.md"
            live.write_text("---\nstatus: production\n---\n\n# Live\n")
            dead.write_text("---\nstatus: superseded\n---\n\n# Dead\n")
            sync = VaultSynchronizer(
                vault_path=vault,
                state_dir=Path(tmpdir) / "state",
            )
            assert sync._peek_note_status(live) == "production"
            assert sync._peek_note_status(dead) == "superseded"
            assert "superseded" in sync.HIDDEN_STATUSES

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            sync._state = {
                "test.md": {"checksum": "abc123", "doc_id": "doc-1", "synced_at": "2026-01-01"}
            }
            sync._save_state()

            # Load in new instance
            sync2 = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            assert "test.md" in sync2._state
            assert sync2._state["test.md"]["doc_id"] == "doc-1"

    def test_full_sync_empty_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            status = sync.full_sync()
            assert status.total_documents == 0
            assert not status.errors
