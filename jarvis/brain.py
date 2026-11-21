from __future__ import annotations

import ast
import logging
import operator
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from config import ROOT, get_settings

logger = logging.getLogger(__name__)
PERSONA_PATH = ROOT / "persona.md"


def _persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8").strip()


def _now_context() -> str:
    now = datetime.now(ZoneInfo("Asia/Manila"))
    return f"Current trusted local time: {now:%A, %B %d, %Y at %I:%M %p} Asia/Manila (UTC+8)."


def _safe_calculation(message: str) -> str | None:
    match = re.search(
        r"(?:what is|calculate|compute)\s+([0-9+*/().%\- ]{3,80})[?!. ]*$",
        message,
        re.IGNORECASE,
    )
    if not match:
        return None
    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ValueError("exponent too large")
            return operations[type(node.op)](left, right)
        raise ValueError("unsupported expression")

    try:
        result = evaluate(ast.parse(match.group(1).strip(), mode="eval"))
        if abs(result) > 1e15:
            return None
        return f"The answer is {result:g}."
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None


def _time_answer(message: str) -> str | None:
    if not re.search(r"\b(time|date|day|today|tomorrow)\b", message, re.IGNORECASE):
        return None
    now = datetime.now(ZoneInfo("Asia/Manila"))
    return f"It is {now:%I:%M %p} on {now:%A, %B %d, %Y}, Philippine time.".replace(
        " 0", " "
    )


def _jarvis_call(prompt: str, model: str) -> str:
    """Run OpenJarvis's simple agent synchronously; called in a worker thread."""
    import os

    os.environ.setdefault("OPENJARVIS_HOME", str(ROOT / ".openjarvis"))
    from openjarvis import Jarvis
    from openjarvis.core.config import JarvisConfig

    # OpenJarvis's LiteLLM engine uses provider/model naming and GROQ_API_KEY.
    settings = get_settings()
    config = JarvisConfig()
    # Keep this app's OpenJarvis calls local to its configured stores and disable
    # both local telemetry collection and external anonymous usage analytics.
    config.telemetry.enabled = False
    config.analytics.enabled = False
    config.traces.enabled = False
    config.security.rate_limit_enabled = False
    config.agent.context_from_memory = settings.jarvis_enable_memory
    address = (
        f' Address the user as "{settings.jarvis_address_as}".'
        if settings.jarvis_address_as
        else " Do not use sir or ma'am."
    )
    config.agent.default_system_prompt = f"{_persona()}\n\n{_now_context()}{address}"
    last_error: Exception | None = None
    for attempt in range(2):
        jarvis = Jarvis(config=config, engine_key="litellm", model=f"groq/{model}")
        try:
            if settings.jarvis_agent == "orchestrator":
                result = jarvis.ask_full(
                    prompt, agent="orchestrator", tools=["calculator", "think"]
                )
                response = (
                    result.get("content", "") if isinstance(result, dict) else result
                )
            else:
                result = jarvis.ask_full(prompt, agent="simple")
            response = result.get("content", "") if isinstance(result, dict) else result
            return str(response).strip()
        except Exception as exc:
            last_error = exc
            status = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if attempt == 0 and status in (429, 500, 502, 503, 504):
                time.sleep(0.7)
                continue
            raise
        finally:
            jarvis.close()
    assert last_error is not None
    raise last_error


async def answer(messages: list[dict[str, str]], model_hint: str | None) -> str:
    from starlette.concurrency import run_in_threadpool

    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("Groq is not configured")
    user_query = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    direct = _time_answer(user_query)
    if direct:
        return direct
    direct = _safe_calculation(user_query)
    if direct:
        return direct

    # The server-selected model wins. Only the explicitly allowed configured ID may be requested.
    model = settings.jarvis_model
    history = "\n".join(f'{m["role"].upper()}: {m["content"]}' for m in messages[-40:])
    prompt = f"Conversation:\n{history}\n\nJ.A.R.V.I.S.:"
    try:
        return await run_in_threadpool(_jarvis_call, prompt, model)
    except Exception as exc:  # noqa: BLE001 -- provider exceptions may contain secrets
        logger.warning("OpenJarvis inference failed (%s)", type(exc).__name__)
        raise RuntimeError("The OpenJarvis/Groq brain is unavailable") from None
