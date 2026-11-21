from __future__ import annotations

import hashlib
import logging
import re

import httpx

from config import ROOT, get_settings

logger = logging.getLogger(__name__)
CACHE_DIR = ROOT / ".cache" / "tts"
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
CODE_RE = re.compile(r"```.*?```|`([^`]*)`", re.DOTALL)
MARKDOWN_RE = re.compile(r"[*_>#~]+")


def clean_text(text: str) -> str:
    text = CODE_RE.sub(r"\1", text)
    text = URL_RE.sub("", text)
    text = MARKDOWN_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 1000:
        logger.info("Truncating TTS text to 1000 characters")
        text = text[:997].rsplit(" ", 1)[0] + "..."
    return text


async def synthesize(text: str) -> tuple[bytes, str]:
    settings = get_settings()
    if not settings.fish_api_key:
        raise RuntimeError("Fish Audio is not configured")
    safe_text = clean_text(text)
    if not safe_text:
        raise ValueError("No speakable text was provided")
    cache_key = hashlib.sha256(
        f"{settings.fish_voice_id}|{settings.fish_model}|{settings.fish_speed}|{safe_text}".encode()
    ).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes(), "audio/mpeg"

    body: dict[str, object] = {
        "text": safe_text,
        "format": "mp3",
        "prosody": {"speed": settings.fish_speed},
    }
    if settings.fish_voice_id:
        body["reference_id"] = settings.fish_voice_id
    headers = {
        "Authorization": f"Bearer {settings.fish_api_key}",
        "model": settings.fish_model,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.fish.audio/v1/tts", headers=headers, json=body
        )
    if response.status_code >= 400:
        logger.warning("Fish Audio request failed with HTTP %d", response.status_code)
        raise RuntimeError("Fish Audio TTS request failed")
    is_mp3_frame = (
        len(response.content) >= 2
        and response.content[0] == 0xFF
        and response.content[1] & 0xE0 == 0xE0
    )
    if not response.content.startswith(b"ID3") and not is_mp3_frame:
        logger.warning("Fish Audio returned an unexpected audio payload")
        raise RuntimeError("Fish Audio returned an invalid audio payload")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(response.content)
    return response.content, "audio/mpeg"
