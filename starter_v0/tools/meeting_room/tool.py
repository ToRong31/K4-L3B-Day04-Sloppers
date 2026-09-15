from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from tools._shared import ROOT, err


DATA_FILE = ROOT / "data" / "meeting_rooms.json"


def _load_data() -> dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _save_data(data: dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_room(rooms: list[dict], room_id: str) -> dict | None:
    for r in rooms:
        if r["room_id"].upper() == room_id.strip().upper():
            return r
    return None


def _get_bookings_for_room(bookings: list[dict], room_id: str, date: str) -> list[dict]:
    return [
        b for b in bookings
        if b["room_id"].upper() == room_id.upper()
        and b["date"] == date
        and b["status"] == "confirmed"
    ]


def _available_slots(room_id: str, date: str, data: dict) -> list[str]:
    all_slots = [
        "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
        "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
    ]
    booked = {b["time_slot"] for b in _get_bookings_for_room(data["bookings"], room_id, date)}
    return [s for s in all_slots if s not in booked]


def meeting_room(
    action: str = "",
    room_id: str = "",
    date: str = "",
    time_slot: str = "",
    capacity: int = 0,
    employee_id: str = "",
    booking_id: str = "",
    confirmed: bool = False,
    top_k: int = 5,
) -> dict[str, Any]:
    try:
        data = _load_data()
    except Exception as exc:
        return err("meeting_room", exc)

    action = (action or "").strip().lower()

    if action == "check_availability":
        return _check_availability(data, room_id, date, time_slot, capacity, top_k)
    elif action == "book_room":
        return _book_room(data, room_id, date, time_slot, employee_id, confirmed)
    elif action == "cancel_booking":
        return _cancel_booking(data, booking_id, confirmed)
    else:
        return {
            "tool": "meeting_room",
            "error": "invalid_action",
            "message": f"Action '{action}' not recognized. Use: check_availability, book_room, cancel_booking.",
        }


def _check_availability(
    data: dict, room_id: str, date: str, time_slot: str, capacity: int, top_k: int
) -> dict[str, Any]:
    if not date or not isinstance(date, str) or len(date.strip()) < 8:
        return {
            "tool": "meeting_room",
            "action": "check_availability",
            "error": "missing_date",
            "message": "Cần cung cấp date dạng YYYY-MM-DD.",
        }

    date = date.strip()

    # Filter by room_id if provided
    rooms = data["rooms"]
    if room_id:
        room = _find_room(rooms, room_id)
        if not room:
            return {
                "tool": "meeting_room",
                "action": "check_availability",
                "error": "room_not_found",
                "room_id": room_id,
                "available_rooms": [r["room_id"] for r in rooms],
            }
        rooms = [room]

    # Filter by capacity
    if capacity and isinstance(capacity, int) and capacity > 0:
        rooms = [r for r in rooms if r["capacity"] >= capacity]
        if not rooms:
            return {
                "tool": "meeting_room",
                "action": "check_availability",
                "error": "no_room_matching_capacity",
                "requested_capacity": capacity,
                "max_available": max((r["capacity"] for r in data["rooms"]), default=0),
            }

    results = []
    for room in rooms[:top_k]:
        booked = _get_bookings_for_room(data["bookings"], room["room_id"], date)
        booked_slots = [b["time_slot"] for b in booked]
        all_slots = [
            "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
            "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
        ]
        available = [s for s in all_slots if s not in booked_slots]

        if time_slot:
            time_slot = time_slot.strip()
            if time_slot in available:
                available = [time_slot]
            else:
                available = []

        results.append({
            "room_id": room["room_id"],
            "name": room["name"],
            "capacity": room["capacity"],
            "equipment": room["equipment"],
            "date": date,
            "available_slots": available,
            "booked_slots": booked_slots,
        })

    return {
        "tool": "meeting_room",
        "action": "check_availability",
        "results": results,
        "total_rooms": len(results),
    }


def _book_room(
    data: dict, room_id: str, date: str, time_slot: str, employee_id: str, confirmed: bool
) -> dict[str, Any]:
    room_id = (room_id or "").strip()
    date = (date or "").strip()
    time_slot = (time_slot or "").strip()
    employee_id = (employee_id or "").strip()

    if not room_id:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "missing_room_id",
            "message": "Cần cung cấp room_id để đặt phòng.",
        }

    room = _find_room(data["rooms"], room_id)
    if not room:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "room_not_found",
            "room_id": room_id,
            "available_rooms": [r["room_id"] for r in data["rooms"]],
        }

    if not date:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "missing_date",
            "message": "Cần cung cấp date dạng YYYY-MM-DD.",
        }

    if not time_slot:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "missing_time_slot",
            "message": "Cần cung cấp time_slot, ví dụ 10:00-11:00.",
            "available_slots": _available_slots(room_id, date, data),
        }

    if not employee_id:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "missing_employee_id",
            "message": "Cần cung cấp employee_id để đặt phòng.",
            "awaiting_user": True,
        }

    # Check conflict
    booked = _get_bookings_for_room(data["bookings"], room_id, date)
    conflict = [b for b in booked if b["time_slot"] == time_slot]
    if conflict:
        available = _available_slots(room_id, date, data)
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "error": "conflict",
            "message": f"Phòng {room_id} đã được đặt {time_slot} ngày {date}.",
            "conflicting_booking": conflict[0]["booking_id"],
            "available_slots": available,
            "awaiting_user": True,
        }

    if not confirmed:
        return {
            "tool": "meeting_room",
            "action": "book_room",
            "status": "needs_confirmation",
            "message": f"Xác nhận đặt phòng {room['name']} ({room_id}) {time_slot} ngày {date} cho {employee_id}?",
            "awaiting_user": True,
            "payload": {
                "room_id": room_id,
                "date": date,
                "time_slot": time_slot,
                "employee_id": employee_id,
            },
        }

    # Create booking
    booking_id = "BK-" + uuid.uuid4().hex[:4].upper()
    new_booking = {
        "booking_id": booking_id,
        "room_id": room_id.upper(),
        "employee_id": employee_id,
        "date": date,
        "time_slot": time_slot,
        "status": "confirmed",
    }
    data["bookings"].append(new_booking)
    _save_data(data)

    return {
        "tool": "meeting_room",
        "action": "book_room",
        "status": "booked",
        "booking_id": booking_id,
        "room": room["name"],
        "room_id": room_id,
        "date": date,
        "time_slot": time_slot,
        "employee_id": employee_id,
    }


def _cancel_booking(data: dict, booking_id: str, confirmed: bool) -> dict[str, Any]:
    booking_id = (booking_id or "").strip()

    if not booking_id:
        return {
            "tool": "meeting_room",
            "action": "cancel_booking",
            "error": "missing_booking_id",
            "message": "Cần cung cấp booking_id để hủy đặt phòng.",
            "awaiting_user": True,
        }

    booking = None
    for b in data["bookings"]:
        if b["booking_id"].upper() == booking_id.upper():
            booking = b
            break

    if not booking:
        return {
            "tool": "meeting_room",
            "action": "cancel_booking",
            "error": "booking_not_found",
            "booking_id": booking_id,
            "message": f"Không tìm thấy đặt phòng {booking_id}.",
        }

    if booking["status"] == "cancelled":
        return {
            "tool": "meeting_room",
            "action": "cancel_booking",
            "error": "already_cancelled",
            "booking_id": booking_id,
            "message": f"Đặt phòng {booking_id} đã bị hủy trước đó.",
        }

    if not confirmed:
        return {
            "tool": "meeting_room",
            "action": "cancel_booking",
            "status": "needs_confirmation",
            "message": f"Xác nhận hủy đặt phòng {booking_id} ({booking['room_id']} {booking['time_slot']} ngày {booking['date']})?",
            "awaiting_user": True,
            "payload": {"booking_id": booking_id},
        }

    booking["status"] = "cancelled"
    _save_data(data)

    return {
        "tool": "meeting_room",
        "action": "cancel_booking",
        "status": "cancelled",
        "booking_id": booking_id,
        "room_id": booking["room_id"],
        "date": booking["date"],
        "time_slot": booking["time_slot"],
    }
