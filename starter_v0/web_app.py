from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chat import run_model_tool_loop, safe_slug, trim_history
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from ui_helpers import (
    new_transcript,
    now_iso,
    parse_agent_payload,
    redact_sensitive_text,
    relative_display_path,
    sanitize_value,
    timestamp_id,
    transcript_bytes,
    write_safe_transcript,
)
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
PROVIDERS = ("openrouter", "openai", "anthropic", "gemini")
PROVIDER_KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
QUICK_ACTIONS = [
    {
        "id": "vpn-status",
        "icon": "pulse",
        "title": "Trạng thái VPN",
        "description": "Kiểm tra dịch vụ production",
        "prompt": "Kiểm tra trạng thái VPN production hiện tại.",
    },
    {
        "id": "device-check",
        "icon": "laptop",
        "title": "Kiểm tra thiết bị",
        "description": "Chẩn đoán laptop LT-204",
        "prompt": "Kiểm tra tổng thể laptop LT-204 giúp tôi.",
    },
    {
        "id": "outlook-guide",
        "icon": "book",
        "title": "Hướng dẫn Outlook",
        "description": "Tìm trong knowledge base",
        "prompt": "Tìm hướng dẫn cấu hình Outlook profile trên Windows 11.",
    },
    {
        "id": "security-advisory",
        "icon": "shield",
        "title": "Cảnh báo bảo mật",
        "description": "Tra CVE công khai cho thiết bị",
        "prompt": "Kiểm tra các CVE và security advisory công khai cho Lenovo ThinkPad T14 Gen 4, BIOS version 1.35.",
    },
    {
        "id": "meeting-room",
        "icon": "meeting",
        "title": "Đặt phòng họp",
        "description": "Xem lịch & đặt phòng họp",
        "prompt": "Xem các phòng họp trống vào ngày 2026-09-16 cho 5 người.",
    },
    {
        "id": "ticket",
        "icon": "ticket",
        "title": "Tạo ticket",
        "description": "Thử luồng xác nhận an toàn",
        "prompt": "Tạo ticket mức high cho lỗi VPN trên LT-204 giúp tôi.",
    },
]

load_lab_env(ROOT)

app = FastAPI(
    title="Slopper IT Helpdesk",
    description="Auditable IT service desk agent with structured tool calling.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

_sessions: dict[str, dict[str, Any]] = {}
_sessions_lock = threading.RLock()


class CreateSessionRequest(BaseModel):
    provider: str = "openrouter"
    version: str = Field(default="v3", min_length=1, max_length=32)
    model: str | None = Field(default=None, max_length=160)
    history_window: int = Field(default=5, ge=1, le=20)
    max_tool_rounds: int = Field(default=4, ge=1, le=8)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=8000)


def _runtime_snapshot(version: str) -> dict[str, Any]:
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    tools = to_openai_tools(declarations)
    artifact_version = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    return {
        "system_prompt": system_prompt,
        "declarations": declarations,
        "tools": tools,
        "artifact_version": artifact_version,
    }


def _provider_info(name: str) -> dict[str, Any]:
    provider = make_provider(name)
    key_name = PROVIDER_KEYS[name]
    return {
        "id": name,
        "label": {
            "openrouter": "OpenRouter",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "gemini": "Google Gemini",
        }[name],
        "default_model": getattr(provider, "default_model", "provider-default"),
        "ready": bool(os.getenv(key_name)),
        "key_env": key_name,
    }


def _public_session(session: dict[str, Any]) -> dict[str, Any]:
    transcript = session["transcript"]
    return {
        "session_id": session["session_id"],
        "provider": transcript["provider"],
        "model": transcript["model"],
        "version": transcript["version"],
        "artifact_version": transcript["artifact_version"],
        "prompt_hash": transcript["prompt_hash"],
        "tools_hash": transcript["tools_hash"],
        "history_window": transcript["history_window"],
        "max_tool_rounds": transcript["max_tool_rounds"],
        "transcript_path": relative_display_path(session["transcript_path"], ROOT),
        "turn_count": len(transcript["turns"]),
        "tool_event_count": sum(len(turn.get("tool_events", [])) for turn in transcript["turns"]),
        "created_at": transcript["created_at"],
        "updated_at": transcript["updated_at"],
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "slopper-helpdesk-ui",
        "time": now_iso(),
        "artifact_files_ready": SYSTEM_PROMPT_PATH.exists() and TOOLS_PATH.exists(),
    }


@app.get("/api/config")
def config() -> dict[str, Any]:
    snapshot = _runtime_snapshot("v3")
    artifact = artifact_version_dict(snapshot["artifact_version"])
    return {
        "app_name": "Slopper",
        "workspace": "Internal IT Service Desk",
        "providers": [_provider_info(name) for name in PROVIDERS],
        "quick_actions": QUICK_ACTIONS,
        "tool_count": len(snapshot["declarations"]),
        "tools": [
            {"name": item["name"], "description": item.get("description", "")}
            for item in snapshot["declarations"]
        ],
        "artifact": artifact,
    }


@app.post("/api/sessions")
def create_session(request: CreateSessionRequest) -> dict[str, Any]:
    provider_name = request.provider.lower().strip()
    if provider_name not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider_name}")

    snapshot = _runtime_snapshot(request.version.strip())
    provider = make_provider(provider_name)
    selected_model = (request.model or "").strip() or getattr(provider, "default_model", "provider-default")
    session_id = "_".join(
        ["ui", safe_slug(request.version), safe_slug(provider_name), timestamp_id()]
    )
    transcript_path = TRANSCRIPTS_DIR / f"{session_id}.transcript.json"
    artifact = snapshot["artifact_version"]
    transcript = new_transcript(
        transcript_id=session_id,
        version=request.version.strip(),
        artifact_version=artifact.artifact_version,
        prompt_hash=artifact.prompt_hash,
        tools_hash=artifact.tools_hash,
        provider=provider_name,
        model=selected_model,
        system_prompt=relative_display_path(SYSTEM_PROMPT_PATH, ROOT),
        tools=relative_display_path(TOOLS_PATH, ROOT),
        history_window=request.history_window,
        max_tool_rounds=request.max_tool_rounds,
    )
    session = {
        "session_id": session_id,
        "system_prompt": snapshot["system_prompt"],
        "tools": snapshot["tools"],
        "transcript": transcript,
        "transcript_path": transcript_path,
        "model_history": [],
        "busy": False,
    }
    with _sessions_lock:
        _sessions[session_id] = session
    write_safe_transcript(transcript_path, transcript)
    return {"session": _public_session(session)}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    with _sessions_lock:
        session = _sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session": _public_session(session),
            "turns": sanitize_value(session["transcript"]["turns"]),
        }


@app.get("/api/sessions/{session_id}/transcript")
def download_transcript(session_id: str) -> Response:
    with _sessions_lock:
        session = _sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        content = transcript_bytes(session["transcript"])
        filename = f"{safe_slug(session_id)}.transcript.json"
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    with _sessions_lock:
        session = _sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session["busy"]:
            raise HTTPException(status_code=409, detail="This session is already processing a request")
        session["busy"] = True
        transcript = session["transcript"]
        turn_index = len(transcript["turns"]) + 1
        history = list(session["model_history"])

    started_at = now_iso()
    started_clock = time.perf_counter()
    safe_user_message, sensitive_labels = redact_sensitive_text(user_message)
    turn: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": started_at,
        "user": safe_user_message,
        "status": "started",
        "assistant_text": None,
        "structured_response": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        if sensitive_labels:
            labels = ", ".join(sorted(set(sensitive_labels)))
            assistant_text = (
                "Mình phát hiện nội dung có thể chứa thông tin xác thực. "
                "Vì an toàn, yêu cầu chưa được gửi tới model hoặc tool và giá trị nhạy cảm đã được che khỏi transcript. "
                "Hãy gửi lại mô tả sự cố mà không kèm password, token, API key, OTP/MFA hay recovery code."
            )
            turn.update(
                {
                    "status": "blocked_sensitive_input",
                    "assistant_text": assistant_text,
                    "security": {"blocked": True, "detected_categories": labels},
                }
            )
        else:
            messages = [
                {"role": "system", "content": session["system_prompt"]},
                *trim_history(history, transcript["history_window"]),
                {"role": "user", "content": user_message},
            ]
            provider = make_provider(transcript["provider"])
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=session["tools"],
                model=transcript["model"],
                max_tool_rounds=transcript["max_tool_rounds"],
            )
            assistant_text = result.get("assistant_text") or ""
            turn.update(result)
            turn["structured_response"] = parse_agent_payload(assistant_text)
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": assistant_text})
    except Exception as exc:
        turn.update(
            {
                "status": "provider_error",
                "assistant_text": (
                    "Mình chưa thể kết nối tới model provider. Hãy kiểm tra API key, model và quota, "
                    "sau đó thử lại. Chi tiết kỹ thuật được lưu trong trace."
                ),
                "error": f"{type(exc).__name__}: {str(exc)}",
            }
        )
    finally:
        turn["ended_at"] = now_iso()
        turn["duration_ms"] = round((time.perf_counter() - started_clock) * 1000)
        safe_turn = sanitize_value(turn)
        with _sessions_lock:
            session = _sessions.get(request.session_id)
            if session:
                session["model_history"] = history
                session["transcript"]["turns"].append(safe_turn)
                session["busy"] = False
                write_safe_transcript(session["transcript_path"], session["transcript"])

    return {
        "turn": safe_turn,
        "session": _public_session(session),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)
