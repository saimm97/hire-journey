"""HTTP-boundary tests for resilient and allowlisted ATS feed fetching."""

from collections.abc import AsyncIterator
from types import SimpleNamespace

import httpx
import pytest

from app.sources import base as source_base

_URL = "https://api.lever.co/v0/postings/acme"
_HOSTS = ("api.lever.co",)


async def _no_sleep(_delay: float) -> None:
    return None


class TrackingStream(httpx.AsyncByteStream):
    def __init__(
        self,
        chunks: list[bytes],
        *,
        fail_after: int | None = None,
    ) -> None:
        self.chunks = chunks
        self.fail_after = fail_after
        self.reads = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            if self.closed:
                return
            if self.fail_after is not None and self.reads == self.fail_after:
                raise httpx.ReadError("stream interrupted")
            self.reads += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def _small_response_settings(monkeypatch, *, maximum: int = 5, attempts: int = 3) -> None:
    monkeypatch.setattr(
        source_base,
        "settings",
        SimpleNamespace(
            ats_max_response_bytes=maximum,
            ats_max_attempts=attempts,
        ),
    )


async def test_fetch_json_retries_rate_limit(monkeypatch):
    requests = 0
    rate_limit_stream = TrackingStream([b"rate limited"])
    success_stream = TrackingStream([b'[{"id": "job-1"}]'])

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                stream=rate_limit_stream,
                request=request,
            )
        return httpx.Response(200, stream=success_stream, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        monkeypatch.setattr(source_base.asyncio, "sleep", _no_sleep)
        result = await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert requests == 2
    assert result == [{"id": "job-1"}]
    assert rate_limit_stream.closed
    assert success_stream.closed


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
    redirect_stream = TrackingStream([])

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(
            302,
            headers={"Location": "https://internal.example.test/jobs"},
            stream=redirect_stream,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="unsafe ATS feed URL"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert requested_hosts == ["api.lever.co"]
    assert redirect_stream.closed


async def test_fetch_json_rejects_invalid_json(monkeypatch):
    stream = TrackingStream([b"not-json"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="not valid JSON"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert stream.closed


async def test_fetch_json_closes_nonretryable_http_error(monkeypatch):
    stream = TrackingStream([b"not found"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, stream=stream, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(httpx.HTTPStatusError):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert stream.closed


async def test_fetch_json_rejects_declared_oversized_response(monkeypatch):
    stream = TrackingStream([b"{}"])
    _small_response_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": "6"},
            stream=stream,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="size limit"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert stream.reads == 0
    assert stream.closed


async def test_fetch_json_stops_stream_without_content_length_at_limit(monkeypatch):
    stream = TrackingStream([b"123", b"456", b"789"])
    _small_response_settings(monkeypatch)
    monkeypatch.setattr(source_base, "_READ_CHUNK_BYTES", 3)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        with pytest.raises(ValueError, match="size limit"):
            await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert stream.reads == 2
    assert stream.closed


async def test_fetch_json_parses_valid_chunked_json_and_closes_stream(monkeypatch):
    stream = TrackingStream([b'{"jo', b'bs":', b" []}"])
    _small_response_settings(monkeypatch, maximum=20)
    monkeypatch.setattr(source_base, "_READ_CHUNK_BYTES", 4)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        result = await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert result == {"jobs": []}
    assert stream.closed


async def test_fetch_json_retries_midstream_transport_failure(monkeypatch):
    first_stream = TrackingStream([b'{"jobs":', b" []}"], fail_after=1)
    second_stream = TrackingStream([b'{"jobs": []}'])
    streams = [first_stream, second_stream]
    _small_response_settings(monkeypatch, maximum=20)
    monkeypatch.setattr(source_base.asyncio, "sleep", _no_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=streams.pop(0), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source_base, "_client", client)
        result = await source_base.fetch_json(_URL, allowed_hosts=_HOSTS)

    assert result == {"jobs": []}
    assert first_stream.closed
    assert second_stream.closed
