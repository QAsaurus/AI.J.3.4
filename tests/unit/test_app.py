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
    import requests
    
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

def test_call_llm_unicode_and_special_characters():
    """
    Unicode test: ensure call_llm works with Cyrillic, Chinese, emoji, and special chars.
    Mock mode should return deterministic response regardless of input text.
    """
    
    # Test mock mode with various Unicode inputs
    test_cases = [
        "Привет мир",  # Cyrillic (Russian)
        "你好世界",      # Chinese
        "مرحبا العالم",  # Arabic
        "👋 Hello 😀",   # Emoji
        "Ñoño 🎉 мир"   # Mixed
    ]
    
    for text in test_cases:
        result = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", [text], mode='mock')
        assert "Mocked Translation" in result, f"Failed for text: {text}"
    
    # Test auth mode with Unicode and mocked post
    monkeypatch_obj = pytest.MonkeyPatch()
    monkeypatch_obj.setenv("MENTORPIECE_API_KEY", "test-key")
    
    def fake_post_unicode(url, json, headers, timeout):
        prompt = json.get("prompt", "")
        return make_mock_response({"response": f"Translation of: {prompt}"}, 200)
    
    with patch("src.app.requests.post", side_effect=fake_post_unicode):
        result = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["中文"], mode='auth')
        assert "Translation of:" in result


def test_call_llm_http_error_statuses(monkeypatch):
    """
    HTTP error test: ensure call_llm handles 400, 401, 403, 404, 500 gracefully.
    All should return error string, not raise exception.
    """
    
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")
    
    error_codes = [400, 401, 403, 404, 500, 502, 503]
    
    for error_code in error_codes:
        def fake_post_error(url, json, headers, timeout):
            return make_mock_response({"error": f"HTTP {error_code}"}, error_code)
        
        with patch("src.app.requests.post", side_effect=fake_post_error):
            result = app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", ["test"], mode='auth')
            # Should return error message, not raise
            assert isinstance(result, str)
            assert "Network/HTTP error" in result, \
                f"Expected error message for status {error_code}, got: {result}"


def test_call_llm_validates_request_payload(monkeypatch):
    """
    Validation test: ensure call_llm sends correct headers and payload structure to API.
    We mock requests.post to capture and verify the actual call arguments.
    """
    
    monkeypatch.setenv("MENTORPIECE_API_KEY", "secret-api-key-123")
    
    with patch("src.app.requests.post") as mock_post:
        mock_post.return_value = make_mock_response({"response": "OK"}, 200)
        
        # Call with auth mode
        test_messages = ["Hello world"]
        app_module.call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", test_messages, mode='auth')
        
        # Verify requests.post was called with correct arguments
        assert mock_post.called, "requests.post should be called in auth mode"
        
        # Get the call arguments
        call_args = mock_post.call_args
        kwargs = call_args.kwargs
        
        # Verify headers contain Authorization
        assert "headers" in kwargs, "Should pass headers dict"
        headers = kwargs["headers"]
        assert "Authorization" in headers, "Should have Authorization header"
        assert headers["Authorization"].startswith("Bearer"), "Should be Bearer token format"
        
        # Verify JSON payload structure
        assert "json" in kwargs, "Should pass json dict"
        json_payload = kwargs["json"]
        assert "model_name" in json_payload, "Payload should have model_name"
        assert "prompt" in json_payload, "Payload should have prompt"