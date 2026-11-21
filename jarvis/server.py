from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from brain import answer
from config import ROOT, configure_logging, get_settings
from voice import synthesize

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=80)
    model: str | None = None

    @field_validator("messages")
    @classmethod
    def history_length(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        return messages[-40:]


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class SlidingRateLimit:
    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        bucket = self.hits[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


limits = SlidingRateLimit()
health_cache: dict[str, tuple[float, bool]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="J.A.R.V.I.S. Local Gateway", lifespan=lifespan)


@app.middleware("http")
async def secure_api(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        settings = get_settings()
        if settings.jarvis_access_token:
            expected = f"Bearer {settings.jarvis_access_token}"
            if request.headers.get("authorization", "") != expected:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if request.method == "POST":
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                length = 0
            body = await request.body()
            if length > 64_000 or len(body) > 64_000:
                return JSONResponse({"error": "Request is too large"}, status_code=413)
            client = request.client.host if request.client else "unknown"
            if not limits.allow(client, settings.jarvis_max_requests_per_minute):
                return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
    return await call_next(request)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        ROOT / "static" / "jarvis_interface.html", media_type="text/html"
    )


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict[str, str]:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="Groq is not configured")
    messages = [message.model_dump() for message in payload.messages]
    if settings.jarvis_debug:
        logger.debug("Chat request messages: %s", messages)
    try:
        reply = await asyncio.wait_for(answer(messages, payload.model), timeout=30)
        return {"reply": reply}
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Assistant timed out") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@app.post("/api/tts")
async def tts(payload: TTSRequest) -> Response:
    try:
        audio, content_type = await synthesize(payload.text)
        return Response(
            audio,
            media_type=content_type,
            headers={"Cache-Control": "private, max-age=3600"},
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


async def service_check(name: str, url: str, key: str) -> bool:
    if not key:
        return False
    cached = health_cache.get(name)
    now = time.monotonic()
    if cached and now - cached[0] < 60:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {key}"})
        healthy = response.is_success
    except httpx.HTTPError:
        healthy = False
    health_cache[name] = (now, healthy)
    return healthy


@app.get("/api/health")
async def health() -> dict[str, bool]:
    settings = get_settings()
    groq_ok, fish_ok = await asyncio.gather(
        service_check(
            "groq", "https://api.groq.com/openai/v1/models", settings.groq_api_key
        ),
        service_check(
            "fish",
            "https://api.fish.audio/wallet/self/api-credit",
            settings.fish_api_key,
        ),
    )
    return {"groq": groq_ok, "fish_audio": fish_ok}


@app.get("/api/digest")
async def digest() -> JSONResponse:
    return JSONResponse(
        {
            "error": "Morning digest is optional and disabled. Configure OpenJarvis connectors before enabling it."
        },
        status_code=501,
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "server:app", host=settings.jarvis_host, port=settings.jarvis_port, reload=False
    )
