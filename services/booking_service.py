"""
艙位訂票系統
"""

import json
from datetime import datetime
from pathlib import Path
from config import DATA_DIR

BOOKING_FILE = DATA_DIR / "bookings.json"

ROUTE_CAPACITY = {
    "KHH-TXG": {"total": 809, "route_name": "高雄港 → 台中港", "price": 12000},
    "TXG-KHH": {"total": 809, "route_name": "台中港 → 高雄港", "price": 12000},
}

CONTAINER_TYPE_FACTOR = {"normal": 1.0, "special": 1.2}


def load_bookings():
    if not BOOKING_FILE.exists():
        return {}
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_bookings(bookings):
    with open(BOOKING_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


def get_available_capacity(route_key: str) -> int:
    bookings = load_bookings()
    total = ROUTE_CAPACITY.get(route_key, {}).get("total", 0)
    booked = sum([b.get("feu_used", 0) for b in bookings.get(route_key, [])])
    return max(0, int(total - booked))


def book_capacity(route_key: str, containers: int, container_type: str = "normal", company_name: str = "") -> dict:
    available = get_available_capacity(route_key)
    feu_needed = containers * CONTAINER_TYPE_FACTOR.get(container_type, 1.0)
    
    if feu_needed > available:
        return {"success": False, "error": f"艙位不足！剩餘 {available} FEU，需要 {feu_needed:.1f} FEU"}
    
    bookings = load_bookings()
    if route_key not in bookings:
        bookings[route_key] = []
    
    booking = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "company_name": company_name,
        "containers": containers,
        "container_type": container_type,
        "feu_used": round(feu_needed, 1),
        "booked_at": datetime.now().isoformat(),
    }
    bookings[route_key].append(booking)
    save_bookings(bookings)
    
    remaining = available - feu_needed
    return {
        "success": True,
        "booking_id": booking["id"],
        "feu_used": round(feu_needed, 1),
        "remaining": int(remaining),
        "total": ROUTE_CAPACITY.get(route_key, {}).get("total", 0),
    }


def get_route_summary():
    summary = {}
    for route_key, info in ROUTE_CAPACITY.items():
        available = get_available_capacity(route_key)
        summary[route_key] = {
            "route_name": info["route_name"],
            "total": info["total"],
            "available": available,
            "booked": info["total"] - available,
            "utilization": round((info["total"] - available) / info["total"] * 100, 1),
        }
    return summary