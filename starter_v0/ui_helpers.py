from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)
_EMBEDDED_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)
_SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "password",
        re.compile(
            r"(?i)\b(password|passwd|mật\s*khẩu)\b(\s*(?:là|is|[:=])\s*)([^\s,;]+)"
        ),
    ),
    (
        "api_key",
        re.compile(r"(?i)\b(api[_\s-]?key|access[_\s-]?key)\b(\s*(?:là|is|[:=])\s*)([^\s,;]+)"),
    ),
    (
        "token",
        re.compile(r"(?i)\b(access[_\s-]?token|refresh[_\s-]?token|token)\b(\s*(?:là|is|[:=])\s*)([^\s,;]+)"),
    ),
    (
        "otp_mfa",
        re.compile(r"(?i)\b(otp|mfa(?:\s*code)?|mã\s*(?:otp|mfa))\b(\s*(?:là|is|[:=])?\s*)(\d{4,10})"),
    ),
    (
        "recovery_code",
        re.compile(r"(?i)\b(recovery[_\s-]?code|mã\s*khôi\s*phục)\b(\s*(?:là|is|[:=])\s*)([^\s,;]+)"),
    ),
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S%f")


def parse_agent_payload(text: str | None) -> dict[str, Any] | None:
    """Parse a structured agent response without assuming every model obeys JSON."""
    if not text:
        return None
    candidate = text.strip()
    embedded = _EMBEDDED_JSON_FENCE_RE.search(candidate)
    if embedded:
        candidate = embedded.group(1).strip()
    else:
        fenced = _CODE_FENCE_RE.match(candidate)
        if fenced:
            candidate = fenced.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def redact_sensitive_text(text: str) -> tuple[str, list[str]]:
    """Redact credential-like values before anything is persisted to disk."""
    redacted = text
    detected: list[str] = []
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(redacted):
            detected.append(label)
            redacted = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
    return redacted, detected


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)[0]
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    return value


def new_transcript(
    *,
    transcript_id: str,
    version: str,
    artifact_version: str,
    prompt_hash: str,
    tools_hash: str,
    provider: str,
    model: str,
    system_prompt: str,
    tools: str,
    history_window: int,
    max_tool_rounds: int,
) -> dict[str, Any]:
    created_at = now_iso()
    return {
        "transcript_id": transcript_id,
        "source": "helpdesk_web_ui",
        "version": version,
        "artifact_version": artifact_version,
        "prompt_hash": prompt_hash,
        "tools_hash": tools_hash,
        "provider": provider,
        "model": model,
        "system_prompt": system_prompt,
        "tools": tools,
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": created_at,
        "updated_at": created_at,
        "redaction_policy": "Credential-like input is blocked and redacted before persistence.",
        "turns": [],
    }


def write_safe_transcript(path: Path, transcript: dict[str, Any]) -> None:
    safe_transcript = sanitize_value(transcript)
    safe_transcript["updated_at"] = now_iso()
    transcript["updated_at"] = safe_transcript["updated_at"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(safe_transcript, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def transcript_bytes(transcript: dict[str, Any]) -> bytes:
    safe_transcript = sanitize_value(transcript)
    return json.dumps(safe_transcript, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def event_state(event: dict[str, Any]) -> tuple[str, str]:
    result = event.get("result")
    if isinstance(result, dict):
        if result.get("error"):
            return "error", "Lỗi"
        if result.get("awaiting_user"):
            return "waiting", "Cần thông tin"
        if result.get("status") == "needs_confirmation":
            return "waiting", "Cần xác nhận"
    return "success", "Hoàn tất"


def relative_display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
