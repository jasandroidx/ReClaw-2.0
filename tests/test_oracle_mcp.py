import os
import json
from unittest.mock import patch

import pytest

from core.oracle_mcp import mcp


class TestOracleMCP:
    @patch("core.oracle_mcp.open")
    @patch("core.oracle_mcp.os.makedirs")
    def test_drain_wal_to_obsidian_path_traversal(self, mock_makedirs, mock_open):
        """
        Test that `_drain_wal_to_obsidian` correctly sanitizes the `connector_name`
        and does not permit path traversal characters like `../`.
        """
        malicious_connector_name = "../../../etc/passwd"
        data = {"test": "payload"}

        mcp._drain_wal_to_obsidian(malicious_connector_name, data)

        mock_makedirs.assert_called()
        mock_open.assert_called()

        # Verify the file was opened with the sanitized path
        called_args, _ = mock_open.call_args
        full_path = called_args[0]

        # 'passwd' comes from basename of malicious string
        assert "___etc_passwd" in full_path or "passwd" in full_path
        assert ".." not in full_path

        # Check that we write the sanitized name to the note
        mock_file_handle = mock_open.return_value.__enter__.return_value
        written_note = mock_file_handle.write.call_args[0][0]
        assert "MCP passwd" in written_note
