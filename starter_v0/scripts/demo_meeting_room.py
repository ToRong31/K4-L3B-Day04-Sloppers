from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import HelpdeskAgent
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools

ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


def run_scenario(agent: HelpdeskAgent, turns: list[str], scenario_name: str) -> dict:
    transcript = {
        "scenario": scenario_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "turns": [],
    }

    history = []
    for i, user_msg in enumerate(turns, 1):
        messages = [
            {"role": "system", "content": agent.system_prompt},
            *history,
            {"role": "user", "content": user_msg},
        ]

        run = agent.run(messages)

        turn_record = {
            "turn": i,
            "user": user_msg,
            "tool_calls": [{"name": c.name, "args": c.args} for c in run.tool_calls],
            "tool_results": run.tool_results,
            "assistant_text": run.text,
        }
        transcript["turns"].append(turn_record)

        history.append({"role": "user", "content": user_msg})
        if run.text:
            history.append({"role": "assistant", "content": run.text})
        for result in run.tool_results:
            history.append({
                "role": "assistant",
                "content": f"TOOL_RESULT: {json.dumps(result, ensure_ascii=False)}",
            })

    transcript["ended_at"] = datetime.now().isoformat(timespec="seconds")
    return transcript


def main() -> None:
    system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    tool_decls = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    openai_tools = to_openai_tools(tool_decls)
    provider = make_provider("openai")
    agent = HelpdeskAgent(provider, system_prompt=system_prompt, tools=openai_tools)

    scenarios = [
        {
            "name": "D1_check_availability",
            "turns": [
                "Phòng MR-301 trống ngày 2026-09-16 những khung giờ nào?",
            ],
        },
        {
            "name": "D2_book_with_confirm",
            "turns": [
                "Đặt phòng MR-301 ngày 2026-09-16 khung 10:00-11:00 cho EMP-1003.",
                "Đúng rồi, xác nhận đặt.",
            ],
        },
        {
            "name": "D3_cancel_then_revoke",
            "turns": [
                "Hủy đặt phòng BK-1001 giúp mình.",
                "Khoan, không hủy nữa.",
            ],
        },
    ]

    transcripts_dir = ROOT / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    all_transcripts = []
    for scenario in scenarios:
        print(f"Running {scenario['name']}...")
        transcript = run_scenario(agent, scenario["turns"], scenario["name"])
        all_transcripts.append(transcript)

        for turn in transcript["turns"]:
            calls = turn["tool_calls"]
            if calls:
                for c in calls:
                    print(f"  Turn {turn['turn']}: {c['name']}({json.dumps(c['args'], ensure_ascii=True)})")
            else:
                print(f"  Turn {turn['turn']}: (no tool call)")
            if turn["assistant_text"]:
                print(f"    -> {turn['assistant_text'][:120]}")
        print()

    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    out_path = transcripts_dir / f"demo_meeting_room_{ts}.json"
    out_path.write_text(json.dumps(all_transcripts, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
