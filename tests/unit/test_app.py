"""
Unit tests for `src/app.py` using pytest.

These tests mock network calls to the MentorPiece API so that no real
requests are made (no tokens consumed). They demonstrate positive flows,
environment-variable handling, and error-handling behavior.

Run with:
    pytest -q

Key techniques used:
 - unittest.mock.patch to replace `requests.post` with a controlled mock
 - os.environ manipulation to simulate presence/absence of API key
 - importlib.reload is not required because `call_llm` reads env at call time

This file contains detailed comments for QA engineers learning pytest and mocking.
"""

import os
import importlib
from unittest.mock import patch, Mock

import pytest

# Import the module under test. We import the functions explicitly for clarity.
from src import app as app_module


def make_mock_response(json_data, status_code=200):
    """
    Helper to create a mock response object that mimics `requests.Response`.

    - `json()` returns `json_data`.
    - `raise_for_status()` raises nothing for 200, or raises a
      requests.exceptions.HTTPError for other status codes.
    """
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data

    def raise_for_status():
        if not (200 <= status_code < 300):
            # Simulate requests' behavior of raising HTTPError for 4xx/5xx
            raise requests.exceptions.HTTPError(f"{status_code} Error")

    mock_resp.raise_for_status.side_effect = raise_for_status
    return mock_resp


def test_call_llm_success_translation_and_judge(monkeypatch):
    """
    Positive test: ensure call_llm returns the expected text for both
    the translation (worker) and judge models when the API responds 200 OK.

    We patch `requests.post` and configure it to return different responses
    depending on the `model_name` in the JSON payload.
    """

    # Test mock mode: no network calls required and deterministic responses
    translation = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["Translate this"], mode='mock')
    assert "Mocked Translation" in translation

    evaluation = app_module.call_llm("claude-sonnet-4-5-20250929", ["Evaluate this"], mode='mock')
    assert "Mocked Grade" in evaluation

    # Now test actual network flow using auth mode with patched requests.post
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key-123")

    def fake_post(url, json, headers, timeout):
        model = json.get("model_name")
        if model.startswith("Qwen"):
            return make_mock_response({"response": "Перевод: Привет мир"}, 200)
        elif model.startswith("claude"):
            return make_mock_response({"response": "Оценка: 9/10 — Хорошо"}, 200)
        else:
            return make_mock_response({"response": "Unknown model"}, 200)

    with patch("src.app.requests.post", side_effect=fake_post) as mock_post:
        translation2 = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["Translate this"], mode='auth')
        assert "Перевод" in translation2
        evaluation2 = app_module.call_llm("claude-sonnet-4-5-20250929", ["Evaluate this"], mode='auth')
        assert "Оценка" in evaluation2


def test_env_var_loading(monkeypatch):
    """
    Environment test: verify call_llm returns a specific error when the
    `MENTORPIECE_API_KEY` is not set, and works when it is set.

    This demonstrates the function reads the env var at call time.
    """

    # Ensure env var is not set
    monkeypatch.delenv("MENTORPIECE_API_KEY", raising=False)

    # Without the API key, auth mode should return an error string
    result = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["text"], mode='auth') 
    assert result.startswith("Error: MENTORPIECE_API_KEY is not set")

    # Mock mode should succeed without needing env var
    result_mock = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["text"], mode='mock')
    assert result_mock.startswith('Mocked Translation')

    # Now provide the API key and patch requests.post to return success for auth mode
    monkeypatch.setenv("MENTORPIECE_API_KEY", "another-test-key")

    with patch("src.app.requests.post") as mock_post:
        mock_post.return_value = make_mock_response({"response": "OK"}, 200)
        result2 = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["text"], mode='auth') 
        assert result2 == "OK"


def test_call_llm_network_error(monkeypatch):
    """
    Error handling test: simulate a network error (requests raises RequestException)
    and ensure call_llm returns a readable error message rather than raising.
    """

    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")

    # Patch requests.post to raise a RequestException to simulate network failure
    import requests

    def raise_conn_error(url, json, headers, timeout):
        raise requests.exceptions.RequestException("connection failed")

    with patch("src.app.requests.post", side_effect=raise_conn_error):
        # Use auth mode to exercise network call path
        result = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["text"], mode='auth') 
        assert result.startswith("Network/HTTP error when calling LLM")
