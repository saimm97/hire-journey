"""HTTP-boundary tests for resilient and allowlisted ATS feed fetching."""

import httpx
import pytest

from app.sources import base as source_base

_URL = "https://api.lever.co/v0/postings/acme"
_HOSTS = ("api.lever.co",)


async def _no_sleep(_delay: float) -> None:
    return None


async def test_fetch_json_retries_rate_limit(monkeypatch):
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(200, json=[{"id": "job-1"}], request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        monkeypatch.setattr(source_base.asyncio, "sleep", _no_sleep)
        result = await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert requests == 2
    assert result == [{"id": "job-1"}]


async def test_fetch_json_retries_transient_network_failure(monkeypatch):
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200, json={"jobs": []}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        monkeypatch.setattr(source_base.asyncio, "sleep", _no_sleep)
        result = await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert requests == 2
    assert result == {"jobs": []}


async def test_fetch_json_rejects_redirect_before_requesting_unknown_host(monkeypatch):
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(
            302,
            headers={"Location": "https://internal.example.test/jobs"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="unsafe ATS feed URL"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert requested_hosts == ["api.lever.co"]


async def test_fetch_json_rejects_invalid_json(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="not valid JSON"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)


async def test_fetch_json_rejects_declared_oversized_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": str(source_base.MAX_RESPONSE_BYTES + 1)},
            content=b"{}",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="size limit"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)
