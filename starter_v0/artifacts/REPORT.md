# Day 04 Lab v3 Report — Trợ lý AI của nhóm

- Lĩnh vực tự chọn:
- Nhiệm vụ và luồng cơ bản đã chốt trước v0:
- Đường dẫn bộ 30 câu cơ bản và 12 câu an toàn; commit chốt bộ trước v0:
- Chức năng mở rộng ngoài luồng cơ bản (nếu có; tối đa 10 trong tổng 100 điểm): meeting_room tool — xem lịch trống, đặt phòng, hủy đặt phòng họp

## Team

- Team:
- Thành viên và INDIVIDUAL: [TEAM.md](../../TEAM.md)
- Members:
- Provider/model:

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

> Viết 1–2 câu mô tả capability và giới hạn của agent.

**Link dùng thử:**

> URL:

## A2. Tool agent có

| Tool | Chức năng | Core / optional / team-built |
|---|---|---|
| clarify | Hỏi bổ sung hoặc xác nhận | core |
| search_kb | Tìm hướng dẫn KB | core |
| check_service_status | Kiểm tra trạng thái dịch vụ | core |
| inspect_device | Chẩn đoán thiết bị | core |
| lookup_user | Tra cứu nhân viên | core |
| format_incident_report | Format báo cáo | core |
| policy | Tìm chính sách IT | optional |
| create_ticket | Tạo ticket hỗ trợ | optional |
| search_device_info | Tìm thông tin thiết bị trên web | optional |
| meeting_room | Quản lý phòng họp: check/book/cancel | **team-built bonus** |

## A3. Câu hỏi mẫu

1.
2.
3.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Cải thiện version | Fallback run/transcript |
|---|---|---|---|
|  |  |  |  |

# PHẦN B — Chi tiết và evidence

Metric chỉ hợp lệ khi `provider_error_cases == 0`, `measured_cases ==
total_cases`, và tool result error đã được review thủ công.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run file |
|---|---|---|---|---:|---:|---|
| v0 | baseline |  |  |  |  |  |
| v1 |  |  |  |  |  |  |
| v2 |  |  |  |  |  |  |
| v3 |  |  |  |  |  |  |

## B2. Failure analysis

| Case ID | Failure type | Actual calls | What failed | Fix |
|---|---|---|---|---|
| MR07_book_then_confirm | wrong_boundary | clarify(yes_no) | Agent gọi clarify lại sau khi user đã confirm ở turn 2. Eval kỳ vọng meeting_room(confirmed=true) trực tiếp. | System prompt cần hướng dẫn: khi user đã nói "xác nhận" rõ ràng, gọi tool với confirmed=true luôn, không clarify lại. |
| MR08_book_then_cancel | wrong_tool | clarify(yes_no) | Agent hỏi confirm hủy thay vì gọi meeting_room(cancel_booking). Eval kỳ vọng tool call đầu tiên là meeting_room. | Agent cần gọi meeting_room(cancel_booking) trước, tool sẽ trả needs_confirmation, sau đó mới clarify. |
| MR10_change_room_confirm | wrong_boundary | clarify(yes_nouse_meeting_room(confirmed=true) dùng room mới | Agent confirm lại phòng cũ MR-405 thay vì dùng MR-301 đã sửa ở turn 2. | Agent cần carry payload mới nhất khi confirm. |

## B3. Team eval cases

Liệt kê đúng 10 case tự viết: 5 single-turn và 5 multi-turn.

| Case ID | What it tests | Expected behavior | Result |
|---|---|---|---|
| MR01 | Check availability by room | meeting_room(check_availability, MR-301, 2026-09-16) | PASS |
| MR02 | Check availability by capacity | meeting_room(check_availability, date, capacity=10) | PASS |
| MR03 | Book without confirm | clarify(yes_no) trước khi book | PASS |
| MR04 | Cancel without confirm | clarify(yes_no) trước khi cancel | PASS |
| MR05 | Room not found | meeting_room(check_availability, MR-999) → error | PASS |
| MR06 | Carry date multi-turn | Carry date từ turn trước sang turn sau | PASS |
| MR07 | Book then confirm | meeting_room(book_room, confirmed=true) sau confirm | FAIL wrong_boundary |
| MR08 | Book then cancel | meeting_room(cancel_booking) khi user muốn hủy | FAIL wrong_tool |
| MR09 | Cancel then revoke | Hủy yêu cầu hủy → no tool | PASS |
| MR10 | Change room confirm | meeting_room(book_room, MR-301, confirmed=true) dùng room mới | FAIL wrong_boundary |

## B4. Live chat evidence

| Scenario/turn | Version | Tool calls + args | Transcript/run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B4a. Adversarial evidence

Phân tích ít nhất 3 cases. Automatic score không chứng minh rằng không có dữ
liệu bị ghi hoặc gửi ra ngoài; cần kiểm tra cả `tool_results` và filesystem.

| Attack case | Expected boundary | Actual calls | Sensitive write/exfiltration occurred? | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Optional và bonus tool evidence

Phần này chỉ điền khi nhóm có sử dụng optional tool hoặc tự xây bonus tool.
Phần chung tối đa 90 điểm; mở rộng tối đa 10 điểm, tổng tối đa 100. Công cụ tự xây để phục vụ luồng cơ bản của lĩnh vực mới thuộc phần chung. `policy`,
`create_ticket` và `search_device_info` là tool có sẵn, không phải tool mới do
nhóm tự xây.

| Category | Evidence file | What worked | Risk / guardrail |
|---|---|---|---|
| Bonus: meeting_room tool | `tools/meeting_room/tool.py`, `data/meeting_rooms.json`, `data/eval_meeting_room.json` | 7/10 pass (base), 3 demo scenarios PASS. Check availability, book with confirm, cancel with revoke all work. Conflict detection returns suggested slots. | Write actions (book/cancel) require confirm. Missing employee_id triggers clarify. Past-time booking not yet blocked. Multi-turn confirmation flow needs prompt improvement. |

## B6. Safety review

- Agent có bao giờ tự đoán asset ID hoặc employee ID không?
- Trace/ticket có chứa password, MFA code, token hay dữ liệu thật không?
- Ticket chỉ được tạo sau xác nhận rõ chưa?
- Tool result error nào cần review thủ công?

## B7. Technical reflection

- Fix nào thuộc `system_prompt.md`?
- Fix nào thuộc `tools.yaml`?
- Failure nào không thể chỉ nhìn automatic score?
- Nếu có thêm một vòng, nhóm sẽ thử hypothesis nào?

# PHẦN C — Checkout trước khi nộp

Phần này được hoàn thành sau khi toàn bộ code, evidence và report đã được đưa
lên repository chung. Nhóm chưa nên nộp link trên VLearn nếu reflection hoặc
commit evidence của bất kỳ thành viên nào còn thiếu.

## C1. Nhận xét chung của nhóm

Hoàn thành mục nhận xét chung trong [TEAM.md](../../TEAM.md). Dẫn tới các run, file và commit trong phần B để chứng minh kết quả. Ghi dưới đây đường dẫn tới mục đã hoàn thành:

> Link:

## C2. INDIVIDUAL của từng thành viên

Mỗi người tự viết và commit mục INDIVIDUAL của mình trong [TEAM.md](../../TEAM.md), nêu phần việc, bằng chứng kỹ thuật và điều đã học. Không yêu cầu chép lại cùng nội dung ở đây. Mỗi mục phải có file/commit/PR thật, không dùng commit tự đánh giá làm bằng chứng kỹ thuật duy nhất.

> Link các mục INDIVIDUAL:

## C3. Final checkout

Chỉ nộp bài khi mọi mục dưới đây đã được kiểm tra trên branch cuối cùng của
repository chung:

- [ ] `TEAM.md` có đủ họ tên, MSSV, GitHub username và vai trò.
- [ ] Mỗi thành viên có ít nhất một commit trong lịch sử branch nộp bài.
- [ ] Phần nhận xét chung trong TEAM.md đã hoàn thành và có evidence.
- [ ] Mỗi thành viên đã tự viết và commit mục INDIVIDUAL trong TEAM.md.
- [ ] `system_prompt.md`, `tools.yaml`, version log, runs, eval, transcript, UI
      và report đã có trong repository.
- [ ] Không có `.env`, API key, token, dữ liệu thật, cache hoặc generated ticket.
- [ ] Nhóm trưởng và mọi thành viên đã thống nhất đúng một URL repository chung.
- [ ] Nhóm trưởng và mọi thành viên sẽ nộp cùng URL đó trên VLearn.

**URL repository chung dùng để nộp:**

> URL:

- [ ] Tên repo đúng mẫu K4-L3-DAY04-HoVaTen-MSSV-PromptEngineeringToolCalling.
- [ ] Kiểm tra deadline và bản chốt theo [SUBMISSION.md](../../SUBMISSION.md).
