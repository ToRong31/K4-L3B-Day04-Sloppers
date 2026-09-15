from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_helpers import (  # noqa: E402
    event_state,
    new_transcript,
    parse_agent_payload,
    redact_sensitive_text,
    transcript_bytes,
    write_safe_transcript,
)
import web_app  # noqa: E402


def main() -> None:
    payload = parse_agent_payload(
        '```json\n{"intent":"device_check","action":"inspect_device","reply":"OK","evidence_ids":[]}\n```'
    )
    assert payload and payload["reply"] == "OK"
    assert parse_agent_payload("plain response") is None
    mixed_payload = parse_agent_payload(
        'Kết quả kiểm tra ở trên.\n\n```json\n{"intent":"status","action":"report","reply":"VPN degraded","evidence_ids":["INC-1042"]}\n```'
    )
    assert mixed_payload and mixed_payload["reply"] == "VPN degraded"

    redacted, labels = redact_sensitive_text("password=Summer2026! và OTP 123456")
    assert "Summer2026!" not in redacted
    assert "123456" not in redacted
    assert set(labels) == {"password", "otp_mfa"}

    assert event_state({"result": {"status": "ok"}}) == ("success", "Hoàn tất")
    assert event_state({"result": {"error": "boom"}}) == ("error", "Lỗi")
    assert event_state({"result": {"awaiting_user": True}}) == ("waiting", "Cần thông tin")

    transcript = new_transcript(
        transcript_id="smoke",
        version="v3",
        artifact_version="v3+pPROMPT+tTOOLS",
        prompt_hash="PROMPT",
        tools_hash="TOOLS",
        provider="fake",
        model="fake-model",
        system_prompt="artifacts/system_prompt.md",
        tools="artifacts/tools.yaml",
        history_window=5,
        max_tool_rounds=4,
    )
    transcript["turns"].append(
        {
            "turn_index": 1,
            "user": "token=secret-value",
            "assistant_text": "Không lưu token.",
            "status": "blocked_sensitive_input",
            "rounds": [],
            "tool_events": [],
        }
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "smoke.transcript.json"
        write_safe_transcript(output, transcript)
        persisted = output.read_text(encoding="utf-8")
        assert "secret-value" not in persisted
        assert "[REDACTED]" in persisted
        assert json.loads(persisted)["source"] == "helpdesk_web_ui"

    download = transcript_bytes(transcript).decode("utf-8")
    assert "secret-value" not in download

    original_transcripts_dir = web_app.TRANSCRIPTS_DIR
    with tempfile.TemporaryDirectory() as temp_dir:
        web_app.TRANSCRIPTS_DIR = Path(temp_dir)
        try:
            client = TestClient(web_app.app)
            health = client.get("/api/health")
            assert health.status_code == 200
            assert health.json()["artifact_files_ready"] is True

            config = client.get("/api/config")
            assert config.status_code == 200
            assert config.json()["tool_count"] >= 1

            created = client.post(
                "/api/sessions",
                json={"provider": "openrouter", "version": "v3"},
            )
            assert created.status_code == 200
            session_id = created.json()["session"]["session_id"]

            blocked = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "password=do-not-save"},
            )
            assert blocked.status_code == 200
            assert blocked.json()["turn"]["status"] == "blocked_sensitive_input"

            saved = client.get(f"/api/sessions/{session_id}/transcript")
            assert saved.status_code == 200
            assert b"do-not-save" not in saved.content
            assert b"[REDACTED]" in saved.content
        finally:
            web_app.TRANSCRIPTS_DIR = original_transcripts_dir

    print("Web UI helper smoke checks: PASS")


if __name__ == "__main__":
    main()
