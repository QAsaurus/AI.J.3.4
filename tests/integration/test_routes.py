"""
Integration tests for the Flask routes using pytest and Flask test client.

These tests simulate the same user flows as the Cypress e2e tests but run
within the Python environment and don't require a display server.

Run with:
    pytest tests/integration/test_routes.py -v

This is a good alternative to Cypress e2e tests for environments without
display servers (like Codespaces headless mode).
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

# Add src to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from app import app


@pytest.fixture
def client():
    """
    Create a Flask test client for making requests to the app.
    The test client simulates a browser sending HTTP requests to our routes.
    """
    with app.test_client() as test_client:
        yield test_client


def make_mock_response(json_data, status_code=200):
    """Helper to create a mock response object."""
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data

    def raise_for_status():
        if not (200 <= status_code < 300):
            import requests
            raise requests.exceptions.HTTPError(f"{status_code} Error")

    mock_resp.raise_for_status.side_effect = raise_for_status
    return mock_resp


def test_index_get_returns_form(client):
    """
    Test GET /: Page loads with the form.
    """
    response = client.get('/')
    assert response.status_code == 200
    assert 'Исходный текст' in response.get_data(as_text=True)  # Check for form label
    assert b'source_text' in response.data  # Check for textarea name


def test_translation_and_judgment_flow(client, monkeypatch):
    """
    Integration test: simulate user entering text, selecting language,
    and submitting the form. Mock the API calls and verify the response.
    """

    # Set the API key
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")

    # Mock requests.post to return translation for Qwen and judgment for Claude
    def fake_post(url, json, headers, timeout):
        model = json.get("model_name")
        if model.startswith("Qwen"):
            return make_mock_response({"response": "Mocked Translation: The sun is shining."}, 200)
        elif model.startswith("claude"):
            return make_mock_response({"response": "Mocked Grade: 9/10. Fluent and accurate."}, 200)
        return make_mock_response({"response": "Unknown model"}, 200)

    with patch("src.app.requests.post", side_effect=fake_post):
        # POST form data with Russian language name
        response = client.post('/', data={
            'source_text': 'Солнце светит.',
            'target_lang': 'Английский',
            'mode': 'mock',
        })

        # Response should be 200 OK
        assert response.status_code == 200

        # Response should contain the mocked translation text
        response_text = response.get_data(as_text=True)
        assert 'Mocked Translation: The sun is shining.' in response_text

        # Response should contain the mocked grade text
        assert 'Mocked Grade: 9/10. Fluent and accurate.' in response_text


def test_empty_text_submission(client, monkeypatch):
    """
    Test edge case: user submits empty text.
    App should show a helpful message.
    """
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")

    response = client.post('/', data={
        'source_text': '',
        'target_lang': 'Английский',
    })

    assert response.status_code == 200
    assert 'Please provide text to translate.' in response.get_data(as_text=True)


def test_api_error_handling(client, monkeypatch):
    """
    Test error handling: when the API returns 500 or connection fails,
    the app shows an error message, not a crash.
    """
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")

    import requests
    def raise_network_error(url, json, headers, timeout):
        raise requests.exceptions.RequestException("Network error")

    with patch("src.app.requests.post", side_effect=raise_network_error):
        response = client.post('/', data={
            'source_text': 'Test text',
            'target_lang': 'Английский',
            'mode': 'auth',
        })

        assert response.status_code == 200
        # Should contain the error message from call_llm
        assert 'Network/HTTP error' in response.get_data(as_text=True)


def test_missing_api_key(client, monkeypatch):
    """
    Test behavior when MENTORPIECE_API_KEY env var is not set.
    The app should display an error, not crash.
    """
    # Ensure API key is not set
    monkeypatch.delenv("MENTORPIECE_API_KEY", raising=False)

    response = client.post('/', data={
        'source_text': 'Test text',
        'target_lang': 'Английский',
        'mode': 'auth',
    })

    assert response.status_code == 200
    # Should contain the missing key error
    assert 'MENTORPIECE_API_KEY is not set' in response.get_data(as_text=True)

@pytest.mark.parametrize("lang", ["Английский", "Французский", "Немецкий", "Португальский"])
def test_all_languages_in_dropdown(client, monkeypatch, lang):
    """
    Test that all language options work correctly.
    Submit form with each language and verify response is 200 OK with mocked translation.
    Uses parametrize to run test once for each language.
    """
    response = client.post('/', data={
        'source_text': 'Test text',
        'target_lang': lang,
        'mode': 'mock',
    })

    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    # In mock mode, should always return the mocked response
    assert 'Mocked Translation' in response_text


def test_boundary_case_very_long_text(client):
    """
    Boundary test: submit very long text (5000+ characters).
    App should handle it without crashing and return mocked response.
    """
    long_text = "A" * 5000  # 5000 character text
    
    response = client.post('/', data={
        'source_text': long_text,
        'target_lang': 'Английский',
        'mode': 'mock',
    })

    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    # Should successfully handle and return mocked response
    assert 'Mocked Translation' in response_text


def test_boundary_case_unicode_text(client):
    """
    Boundary test: submit text with Unicode (Russian, Chinese, emoji).
    App should handle Unicode correctly and return mocked response.
    """
    unicode_texts = [
        "Привет мир 🌍",  # Russian + emoji
        "你好世界",        # Chinese
        "مرحبا 👋",       # Arabic + emoji
    ]

    for text in unicode_texts:
        response = client.post('/', data={
            'source_text': text,
            'target_lang': 'Английский',
            'mode': 'mock',
        })

        assert response.status_code == 200
        response_text = response.get_data(as_text=True)
        # Should handle Unicode and return mocked translation
        assert 'Mocked Translation' in response_text


def test_different_http_error_codes(client, monkeypatch):
    """
    Test that different HTTP error codes (400, 401, 403, 404, 500) are handled gracefully.
    App should show error message instead of crashing.
    """
    monkeypatch.setenv("MENTORPIECE_API_KEY", "test-key")

    error_codes = [400, 401, 403, 404, 500]

    for error_code in error_codes:
        def fake_post_error(url, json, headers, timeout):
            return make_mock_response({"error": f"HTTP {error_code}"}, error_code)

        with patch("src.app.requests.post", side_effect=fake_post_error):
            response = client.post('/', data={
                'source_text': 'Test text',
                'target_lang': 'Английский',
                'mode': 'auth',
            })

            assert response.status_code == 200, f"Should return 200 even on HTTP {error_code}"
            response_text = response.get_data(as_text=True)
            # Should contain error indication
            assert 'Network/HTTP error' in response_text, f"Should show error for HTTP {error_code}"