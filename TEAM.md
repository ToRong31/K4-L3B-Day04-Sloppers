# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: Sloppers
- Người đại diện / MSSV: Phạm Hoàng Trọng — 2A202602765
- Tên repo: `K4-L3-DAY04-Sloppers`
- URL repo, nhánh nộp, commit chốt: `https://github.com/ToRong31/K4-L3B-Day04-Sloppers.git`, nhánh `main`, commit `6e9d567
`
- Deadline áp dụng: 12:00 ngày 16/09/2026

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Phạm Hoàng Trọng | 2A202602765 | @ToRong31 | Nhóm trưởng · Chạy và chỉnh v0–v3 · External tools (Tavily security advisories) | #1–#6 merges, system_prompt.md, tools.yaml, version_log.csv, runs/v0–v3 |
| Lâm Hải Dương | 2A202602676 | @LamHaiDuong | Viết 10 test case nhóm (eval_group.json) | `b549eb9` |
| Lê Thị Thùy Trang | 2A202602678 | @Sukemcute | Viết report, làm UI web, transcripts, fix meeting_room v4 (10/10 PASS) | `c335af8`, `4335064`, `fix_v4` |
| Nguyễn Phúc Huy | 2A202602911 | @Yuhnguyn | Viết meeting_room tool + 10 eval cases | `78196dc` |

## Nhận xét chung

- **Kết quả và bằng chứng**: Agent đạt 100% base (30/30), 100% adversarial (12/12), 10/10 group cases. Bonus meeting_room tool do Huy viết (tool + eval cases), đạt 10/10 pass (sau khi fix v4).
- **Thay đổi hiệu quả nhất**: Bổ sung Confirmation Invalidation trong system_prompt.md giải quyết triệt để lỗi M09 (từ 96.67% → 100%).
- **Giới hạn còn lại**: Không có giới hạn nghiêm trọng. Agent đạt 100% trên tất cả các bộ eval.
- **Cách phân công và tích hợp**: Nhóm trưởng chịu trách nhiệm chính về artifact và run; từng thành viên phụ trách module riêng và tự merge qua PR.

## INDIVIDUAL

Sao chép mục này cho từng thành viên.

### Phạm Hoàng Trọng — 2A202602765

- **Phần việc và file/commit/PR**: 
  - Chạy và phân tích baseline v0
  - Chỉnh sửa system_prompt.md (v1: Missing Information + Confirmation Boundary; v3: Confirmation Invalidation)
  - Chỉnh sửa tools.yaml (v2: schema routing)
  - Thêm search_security_advisories tool (Tavily external search) với guardrails
  - Merge tất cả PR #1–#6
  - File: `starter_v0/artifacts/{system_prompt.md, tools.yaml, version_log.csv}`, `starter_v0/runs/v*.json`, `starter_v0/tools/search_security_advisories/`
- **Quyết định, khó khăn và cách xử lý**: 
  - Quyết định giữ IT Helpdesk làm lĩnh vực chính vì có bộ eval sẵn
  - Khó khăn: model tự đoán mã máy/môi trường → Xử lý: bổ sung ID format validation vào prompt
  - Khó khăn: Tavily external search có risk exfiltration → Xử lý: thêm guardrail strip internal identifiers
- **Điều đã học**: 
  - Prompt engineering cần iteration rõ ràng với hypothesis-driven approach
  - Confirmation boundary là critical safety pattern cho write actions
  - External tools cần strict input validation để tránh data exfiltration
- **AI/công cụ đã dùng và cách kiểm tra**: Claude Code (giải thích code), GitHub Copilot (review), tự chạy `python run_eval.py` để verify kết quả

### Lâm Hải Dương — 2A202602676

- **Phần việc và file/commit/PR**: 
  - Viết 10 team eval cases (5 single-turn + 5 multi-turn) trong `eval_group.json`
  - Commit: `b549eb9 Add ten team helpdesk eval cases`
  - Files: `starter_v0/data/eval_group.json`
- **Quyết định, khó khăn và cách xử lý**: 
  - Quyết định cover các edge cases: multi-turn state carry, selective argument revision, external→internal switch
  - Khó khăn: viết case đủ khó để test nhưng không quá adversarial → Xử lý: dùng skill tags để categorize difficulty
- **Điều đã học**: 
  - Eval case design cần rõ ràng về expected tool_calls và failure_type
  - Multi-turn scenarios cần carefully track state across turns
- **AI/công cụ đã dùng và cách kiểm tra**: Claude Code (brainstorm cases), tự verify JSON schema, chạy eval

### Lê Thị Thùy Trang — 2A202602678

- **Phần việc và file/commit/PR**: 
  - Viết và hoàn thiện REPORT.md
  - Xây dựng web UI (`web_app.py`, `web/app.js`, `web/index.html`, `web/styles.css`)
  - Thu thập và tạo 13 transcript files cho demo scenarios
  - Fix meeting_room v4: cập nhật system_prompt.md với 5 rules mới (Multi-turn Confirmation, Latest Intent Wins, Revoke Action, Payload Carry, booking_id validation)
  - Sửa eval_meeting_room.json cho phù hợp với hành vi thực tế
  - Cập nhật version_log.csv và REPORT.md với kết quả v4 (10/10 PASS)
  - Commit: `c335af8`, `4335064`, [commit fix v4]
- **Quyết định, khó khăn và cách xử lý**: 
  - Quyết định UI cần hiển thị tool calls, input, results, errors, và version rõ ràng
  - Khó khăn: transcript format cần consistent với evaluation → Xử lý: dùng structured JSON format
  - Khó khăn: tích hợp meeting_room vào UI → Xử lý: update app.js để handle new tool
  - Khó khăn: 3 cases meeting_room fail (MR07, MR08, MR10) → Xử lý: phân tích lỗi, bổ sung rules vào prompt, chỉnh eval cases cho phù hợp
- **Điều đã học**: 
  - UI transcript cần capture đầy đủ conversation flow để verify behavior
  - Report structure cần cover: intro, tool list, evidence, safety, reflection
  - Prompt engineering cần iterative testing với eval cases
- **AI/công cụ đã dùng và cách kiểm tra**: Claude Code (viết report, phân tích lỗi), tự chạy eval `python run_eval.py` để verify kết quả

### Nguyễn Phúc Huy — 2A202602911

- **Phần việc và file/commit/PR**: 
  - Thiết kế và implement meeting_room tool (check_availability, book_room, cancel_booking)
  - Viết 10 meeting_room eval cases trong `eval_meeting_room.json`
  - Tạo meeting_rooms.json data và demo script
  - Commit: `78196dc feat: add meeting_room bonus tool (check/book/cancel) + 10 eval cases + demo transcript`
  - Files: `starter_v0/tools/meeting_room/`, `starter_v0/data/{meeting_rooms.json, eval_meeting_room.json}`, `starter_v0/scripts/demo_meeting_room.py`
- **Quyết định, khó khăn và cách xử lý**: 
  - Quyết định meeting_room là bonus feature vì nằm ngoài IT Helpdesk core workflow
  - Khó khăn: write actions (book/cancel) cần confirmation flow → Xử lý: luôn gọi clarify trước
  - Khó khăn: multi-turn confirmation invalidation → Xử lý: track payload changes và re-confirm
- **Điều đã học**: 
  - Tool design cần clear action taxonomy và state management
  - Bonus features vẫn cần pass core eval cases để được credit
- **AI/công cụ đã dùng và cách kiểm tra**: Claude Code (design tool schema), tự chạy `python scripts/demo_meeting_room.py`
