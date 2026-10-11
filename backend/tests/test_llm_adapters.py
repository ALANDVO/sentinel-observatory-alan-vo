"""Tests for the LLM adapters service: offline fallback, credential redaction, provider switching."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.llm_adapters import LLMAdapters, _redact_error, LLMAdapterError


@pytest.fixture
def unconfigured_adapter():
    """Adapter with no LLM_API_KEY configured."""
    with patch.dict(os.environ, {"LLM_API_KEY": "", "LLM_PROVIDER": "openai-compatible"}):
        yield LLMAdapters()


@pytest.fixture
def configured_adapter():
    """Adapter with a synthetic API key."""
    synthetic_key = "sk-" + "0" * 48  # Clearly synthetic, not a real credential
    with patch.dict(os.environ, {"LLM_API_KEY": synthetic_key, "LLM_PROVIDER": "openai-compatible"}):
        yield LLMAdapters()


def test_offline_fallback_when_no_api_key(unconfigured_adapter: LLMAdapters):
    result = unconfigured_adapter.analyze_deck("AI Safety", ["Alignment overview", "RLHF methods"])
    assert result["offline"] is True
    assert result["provider"] == "offline"
    assert result["advisory"] is not None
    assert "AI Safety" in result["advisory"]


def test_offline_advisory_includes_deck_title(unconfigured_adapter: LLMAdapters):
    result = unconfigured_adapter._offline_advisory("Neural Network Safety", ["Interpretability", "Robustness"], "review")
    assert "Neural Network Safety" in result["advisory"]
    assert "[Offline" in result["label"]


def test_advisory_label_present_in_response(unconfigured_adapter: LLMAdapters):
    result = unconfigured_adapter.analyze_deck("Benchmarks", ["F1 score analysis"])
    assert "label" in result
    assert len(result["label"]) > 5


def test_is_configured_false_without_key(unconfigured_adapter: LLMAdapters):
    assert not unconfigured_adapter.is_configured()


def test_is_configured_true_with_key(configured_adapter: LLMAdapters):
    assert configured_adapter.is_configured()


def test_credential_redaction_sk_pattern():
    # Generate a synthetic value following the sk- pattern for redaction testing
    synthetic_secret = "sk-" + "a" * 30
    msg = f"Authorization failed for {synthetic_secret}"
    redacted = _redact_error(msg)
    assert synthetic_secret not in redacted
    assert "[REDACTED]" in redacted


def test_credential_redaction_bearer_pattern():
    synthetic_token = "Bearer " + "x" * 32
    msg = f"Request failed with {synthetic_token}"
    redacted = _redact_error(msg)
    assert "x" * 32 not in redacted
    assert "[REDACTED]" in redacted


def test_openai_compatible_request_format(configured_adapter: LLMAdapters):
    """Verify that the OpenAI-compatible adapter sends the correct JSON structure."""
    captured_payload = {}

    def fake_post(url, json=None, headers=None, **kwargs):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Test advisory"}}]}
        return mock_resp

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = fake_post
        mock_client_cls.return_value = mock_client

        result = configured_adapter._call_openai_compatible("Test prompt")
        assert result == "Test advisory"
        assert "model" in captured_payload
        assert "messages" in captured_payload
        assert captured_payload["messages"][0]["role"] == "user"


def test_unknown_provider_raises_error():
    with patch.dict(os.environ, {"LLM_API_KEY": "sk-" + "0" * 48, "LLM_PROVIDER": "unknown-provider"}):
        adapter = LLMAdapters()
    with pytest.raises(LLMAdapterError, match="Unknown provider"):
        adapter._call_provider("Test prompt")


def test_provider_error_returns_error_key_not_raising(configured_adapter: LLMAdapters):
    """Provider HTTP errors should be caught and returned as error key, not re-raised."""
    import httpx

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        result = configured_adapter.analyze_deck("Test Deck", ["Slide 1"])
        assert "error" in result
        assert result["advisory"] is None
