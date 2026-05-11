"""
艙位訂票系統 - 完整船期管理 + 客戶訂票記錄
"""

import json
from datetime import datetime
from pathlib import Path
from config import DATA_DIR

SHIPS_FILE = DATA_DIR / "ships_schedule.json"
BOOKING_FILE = DATA_DIR / "bookings.json"


def load_ships_data():
    if not SHIPS_FILE.exists():
        return {}
    try:
        with open(SHIPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_ships_data(ships_data):
    with open(SHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(ships_data, f, ensure_ascii=False, indent=2)


def load_bookings():
    if not BOOKING_FILE.exists():
        return []
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_bookings(bookings):
    with open(BOOKING_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


# ================= 以下是 app.py 需要的函數 =================

def get_available_capacity(route_key: str) -> int:
    """取得航線可用艙位（總和）"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    total_remaining = 0
    for ship in route_data:
        remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
        total_remaining += remaining
    return total_remaining


def get_total_capacity(route_key: str) -> int:
    """取得航線總艙位"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    total = 0
    for ship in route_data:
        total += ship["capacity_teu"]
    return total


def get_route_summary():
    """取得所有航線艙位摘要"""
    ships_data = load_ships_data()
    summary = {}
    for route_key, route_data in ships_data.items():
        total_capacity = 0
        total_remaining = 0
        for ship in route_data.get("ships", []):
            total_capacity += ship["capacity_teu"]
            remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
            total_remaining += remaining
        summary[route_key] = {
            "route_name": route_data.get("route_name", route_key),
            "total_capacity": total_capacity,
            "available_capacity": total_remaining,
            "utilization": round((total_capacity - total_remaining) / total_capacity * 100, 1) if total_capacity > 0 else 0
        }
    return summary


def get_all_ships_summary(route_key: str):
    """取得所有船班艙位摘要"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    
    summary = []
    for ship in route_data:
        remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
        utilization = round((ship["capacity_teu"] - remaining) / ship["capacity_teu"] * 100, 1)
        
        summary.append({
            "voyage_no": ship["voyage_no"],
            "ship_name": ship["ship_name"],
            "sailing_date": ship["sailing_date"],
            "sailing_day": ship["sailing_day"],
            "capacity": ship["capacity_teu"],
            "market_booked": ship["market_booked_teu"],
            "user_booked": ship["user_booked_teu"],
            "remaining": remaining,
            "utilization": utilization,
            "eta_port": ship.get("eta_port", ""),
            "eta_time": ship.get("eta_time", ""),
            "cutoff_time": ship.get("cutoff_time", "")
        })
    
    return summary


def get_customer_bookings(company_name: str = None):
    """取得客戶訂票記錄"""
    bookings = load_bookings()
    if company_name:
        return [b for b in bookings if b.get("company_name") == company_name]
    return bookings


def get_upcoming_ships(days_ahead: int = 30):
    """取得未來船班"""
    ships_data = load_ships_data()
    all_ships = []
    today = datetime.now().date()
    
    for route_key, route_data in ships_data.items():
        for ship in route_data.get("ships", []):
            sailing_date = datetime.strptime(ship["sailing_date"], "%Y-%m-%d").date()
            days_until = (sailing_date - today).days
            if 0 <= days_until <= days_ahead:
                remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
                all_ships.append({
                    "route_key": route_key,
                    "route_name": route_data.get("route_name", route_key),
                    "voyage_no": ship["voyage_no"],
                    "ship_name": ship["ship_name"],
                    "sailing_date": ship["sailing_date"],
                    "sailing_day": ship["sailing_day"],
                    "days_until": days_until,
                    "remaining": remaining,
                    "capacity": ship["capacity_teu"],
                    "eta_port": ship.get("eta_port", ""),
                    "eta_time": ship.get("eta_time", "")
                })
    
    return sorted(all_ships, key=lambda x: x["sailing_date"])


def get_booking_summary():
    """取得訂票摘要統計"""
    bookings = load_bookings()
    total_bookings = len(bookings)
    total_containers = sum(b.get("containers", 0) for b in bookings)
    total_customers = len(set(b.get("company_name") for b in bookings))
    
    return {
        "total_bookings": total_bookings,
        "total_containers": total_containers,
        "total_customers": total_customers,
        "recent_bookings": bookings[-10:] if bookings else []
    }


def book_capacity(route_key: str, sailing_date: str, containers: int, company_name: str, contact_person: str = "", phone: str = "") -> dict:
    """預訂艙位 - 動態減少艙位"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {})
    ships = route_data.get("ships", [])
    
    target_ship = None
    for ship in ships:
        if ship["sailing_date"] == sailing_date:
            target_ship = ship
            break
    
    if not target_ship:
        return {"success": False, "error": f"找不到 {sailing_date} 的船班"}
    
    current_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship["user_booked_teu"]
    
    if containers > current_remaining:
        return {
            "success": False, 
            "error": f"艙位不足！剩餘 {current_remaining} TEU，需要 {containers} TEU",
            "remaining": current_remaining
        }
    
    target_ship["user_booked_teu"] += containers
    save_ships_data(ships_data)
    
    new_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship["user_booked_teu"]
    utilization = round((target_ship["capacity_teu"] - new_remaining) / target_ship["capacity_teu"] * 100, 1)
    
    booking = {
        "booking_id": f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "booking_time": datetime.now().isoformat(),
        "company_name": company_name,
        "contact_person": contact_person,
        "phone": phone,
        "route_key": route_key,
        "route_name": route_data.get("route_name", route_key),
        "sailing_date": sailing_date,
        "sailing_day": target_ship["sailing_day"],
        "voyage_no": target_ship["voyage_no"],
        "ship_name": target_ship["ship_name"],
        "containers": containers,
        "eta_port": target_ship.get("eta_port", ""),
        "eta_time": target_ship.get("eta_time", ""),
        "status": "confirmed"
    }
    bookings = load_bookings()
    bookings.append(booking)
    save_bookings(bookings)
    
    return {
        "success": True,
        "booking_id": booking["booking_id"],
        "voyage_no": target_ship["voyage_no"],
        "ship_name": target_ship["ship_name"],
        "sailing_date": sailing_date,
        "sailing_day": target_ship["sailing_day"],
        "containers": containers,
        "remaining": new_remaining,
        "capacity": target_ship["capacity_teu"],
        "utilization": utilization,
        "eta_port": target_ship.get("eta_port", ""),
        "eta_time": target_ship.get("eta_time", ""),
        "message": f"成功預訂 {containers} TEU，剩餘 {new_remaining} TEU"
    }