import pytest
import os
import requests
from unittest.mock import patch, MagicMock
from clients.occupancy import OccupancyClient

def test_occupancy_client_paper_state(monkeypatch):
    monkeypatch.delenv("KEEP_PULSE_URL", raising=False)
    client = OccupancyClient()
    result = client.get_occupancy()
    assert result["status"] == "paper"
    assert result["occupants"] == 0
    assert "KEEP_PULSE_URL not set" in result["message"]

@patch('clients.occupancy.requests.get')
def test_occupancy_client_empty_state(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"occupants": []}
    mock_get.return_value = mock_response

    client = OccupancyClient(pulse_url="http://example.com/pulse")
    result = client.get_occupancy()

    assert result["status"] == "empty"
    assert result["occupants"] == 0
    assert "No occupants" in result["message"]

@patch('clients.occupancy.requests.get')
def test_occupancy_client_live_state(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"occupants": [{"name": "Agent Smith"}]}
    mock_get.return_value = mock_response

    client = OccupancyClient(pulse_url="http://example.com/pulse")
    result = client.get_occupancy()

    assert result["status"] == "live"
    assert result["count"] == 1
    assert result["occupants"][0]["name"] == "Agent Smith"

@patch('clients.occupancy.requests.get')
def test_occupancy_client_error_state_404(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    client = OccupancyClient(pulse_url="http://example.com/pulse")
    result = client.get_occupancy()

    assert result["status"] == "empty"
    assert result["occupants"] == 0

@patch('clients.occupancy.requests.get')
def test_occupancy_client_error_state_500(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    client = OccupancyClient(pulse_url="http://example.com/pulse")
    result = client.get_occupancy()

    assert result["status"] == "error"
    assert result["occupants"] == 0
    assert "status code 500" in result["message"]

@patch('clients.occupancy.requests.get')
def test_occupancy_client_error_state_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

    client = OccupancyClient(pulse_url="http://example.com/pulse")
    result = client.get_occupancy()

    assert result["status"] == "error"
    assert result["occupants"] == 0
    assert "Connection error" in result["message"]
