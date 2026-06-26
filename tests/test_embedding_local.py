"""Unit tests for UX-04: Ollama-compatible local embedder fallback."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_ollama_provider_returns_openai_compatible_provider(monkeypatch):
    """EMBEDDING_PROVIDER=ollama returns an OpenAIEmbeddingProvider (Ollama-compat)."""
    from common.embedding._registry import get_embedding_provider
    from common.embedding.providers.openai import OpenAIEmbeddingProvider

    p = get_embedding_provider("ollama")
    assert isinstance(p, OpenAIEmbeddingProvider)


def test_ollama_provider_uses_default_url_and_model(monkeypatch):
    """Defaults to localhost:11434/v1 and mxbai-embed-large."""
    monkeypatch.delenv("OLLAMA_EMBEDDING_URL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)

    from common.embedding._registry import _openai_provider_cache, get_embedding_provider

    _openai_provider_cache.clear()
    p = get_embedding_provider("ollama")
    assert p._base_url == "http://localhost:11434/v1"
    assert p.model == "mxbai-embed-large"


def test_ollama_provider_respects_env_overrides(monkeypatch):
    """OLLAMA_EMBEDDING_URL and OLLAMA_EMBEDDING_MODEL override defaults."""
    monkeypatch.setenv("OLLAMA_EMBEDDING_URL", "http://gpu-box:11434/v1")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    from common.embedding._registry import _openai_provider_cache, get_embedding_provider

    _openai_provider_cache.clear()
    p = get_embedding_provider("ollama")
    assert p._base_url == "http://gpu-box:11434/v1"
    assert p.model == "nomic-embed-text"


def test_ollama_provider_does_not_send_dimensions(monkeypatch):
    """Ollama provider never sends dimensions= (Ollama rejects it)."""
    from common.embedding._registry import _openai_provider_cache, get_embedding_provider

    _openai_provider_cache.clear()
    p = get_embedding_provider("ollama")
    assert p._send_dimensions is False


def test_unknown_provider_raises(monkeypatch):
    """Unknown provider name raises ValueError."""
    from common.embedding._registry import get_embedding_provider

    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedding_provider("not-a-real-provider")
