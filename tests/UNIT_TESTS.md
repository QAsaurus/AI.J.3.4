Unit tests for AI Translator & Critic
===================================

Overview
--------
This document explains the unit tests created for `src/app.py`.

Files
-----
- `tests/unit/test_app.py` — pytest-based unit tests covering:
  - Successful LLM responses for translation and judge models (mocked).
  - Environment variable handling (when `MENTORPIECE_API_KEY` is missing/present).
  - Error handling when the requests library raises network errors.

Key points for QA engineers
--------------------------
- All network calls to `https://api.mentorpiece.org/v1/process-ai-request` are mocked
  using `unittest.mock.patch` of `src.app.requests.post`.
- `call_llm` reads the `MENTORPIECE_API_KEY` from the environment at call time,
  which allows tests to set or remove this env var with `monkeypatch.setenv` or
  `monkeypatch.delenv`.
- The mocked `requests.post` returns a small fake response object where
  `.json()` returns the expected structure: `{"response": "..."}`.

Run the tests
-------------
1. Install test dependencies (if not already installed):

```bash
pip install pytest
```

2. Run tests from the repository root:

```bash
pytest -q
```

Notes
-----
- The tests purposefully avoid any real network I/O to keep them fast,
  deterministic, and safe to run in CI without exposing API keys or consuming tokens.
- If you need to extend tests to cover the Flask routes themselves, consider using
  Flask's `test_client()` and patching `call_llm` to return canned responses.
