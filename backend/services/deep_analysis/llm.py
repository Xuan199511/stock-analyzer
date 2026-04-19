"""Shared Claude client for deep-analysis LLM calls.

Uses claude-sonnet-4-6 per project convention.  Returns empty dict on
any failure (caller picks up ``errors``) so partial reports can still ship.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Optional

import anthropic

from .logging_config import logger

CLAUDE_MODEL = "claude-sonnet-4-6"
_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_log = logger.bind(section="llm")


def available() -> bool:
    return bool(_API_KEY)


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


async def call_json(
    prompt: str,
    max_tokens: int = 2048,
    system: Optional[str] = None,
) -> dict[str, Any]:
    """Send prompt, expect JSON back.  Raises on any failure (caller handles)."""
    if not _API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.AsyncAnthropic(api_key=_API_KEY)
    t0 = time.perf_counter()
    try:
        msg = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system or "你是專業的股票研究分析師。請嚴格以 JSON 回傳，不要有多餘文字或 markdown 包裝。",
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        _log.error(f"Claude HTTP {e.status_code}: {e.message}")
        raise
    except anthropic.APIError as e:
        _log.error(f"Claude API error: {e}")
        raise

    dt = time.perf_counter() - t0
    usage = getattr(msg, "usage", None)
    tokens_in  = getattr(usage, "input_tokens",  None) if usage else None
    tokens_out = getattr(usage, "output_tokens", None) if usage else None
    _log.info(f"{CLAUDE_MODEL} {dt:.2f}s in={tokens_in} out={tokens_out}")

    raw = _strip_fences(msg.content[0].text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        _log.warning(f"JSON parse error: {e} · raw[:200]={raw[:200]}")
        raise RuntimeError(f"Claude JSON parse error: {e}")
