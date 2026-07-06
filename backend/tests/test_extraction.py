"""Tests for schema-validated LLM extraction with retry and provider fallback."""

import pytest
from pydantic import BaseModel

from app.exceptions import ExtractionError
from app.utils import llm


class _Schema(BaseModel):
    name: str


class _FakeLLM:
    """Chat-model stand-in whose queued results are returned or raised in order."""

    def __init__(self, results):
        self._results = list(results)

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, messages):
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _patch_providers(monkeypatch, providers):
    monkeypatch.setattr(llm, "build_providers", lambda temperature=0.0: providers)


async def test_returns_valid_result(monkeypatch):
    _patch_providers(monkeypatch, [_FakeLLM([_Schema(name="ok")])])
    result = await llm.structured_extract("sys", "user", _Schema)
    assert result.name == "ok"


async def test_retries_after_a_failure(monkeypatch):
    _patch_providers(monkeypatch, [_FakeLLM([ValueError("bad json"), _Schema(name="recovered")])])
    result = await llm.structured_extract("sys", "user", _Schema, retries=1)
    assert result.name == "recovered"


async def test_no_provider_raises(monkeypatch):
    _patch_providers(monkeypatch, [])
    with pytest.raises(ExtractionError):
        await llm.structured_extract("sys", "user", _Schema)


async def test_exhausted_retries_raise(monkeypatch):
    _patch_providers(monkeypatch, [_FakeLLM([ValueError("x"), ValueError("y")])])
    with pytest.raises(ExtractionError):
        await llm.structured_extract("sys", "user", _Schema, retries=1)
