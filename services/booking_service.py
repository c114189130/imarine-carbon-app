"""
艙位訂票系統 - 完整版
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from config import DATA_DIR
from services.market_simulator import get_market_booking_rate, get_port_congestion, calculate_dynamic_price

SHIPS_FILE = DATA_DIR / "ships_schedule.json"
BOOKING_FILE = DATA_DIR / "bookings.json"
_booking_lock = Lock()


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


def apply_market_simulation():
    ships_data = load_ships_data()
    updated = False
    for route_key, route_data in ships_data.items():
        for ship in route_data.get("ships", []):
            if ship["sailing_date"] < datetime.now().strftime("%Y-%m-%d"):
                continue
            market_demand = get_market_booking_rate(ship["sailing_date"])
            current_used = ship["market_booked_teu"] + ship.get("user_booked_teu", 0)
            max_possible = ship["capacity_teu"] - current_used
            new_market_booked = min(market_demand, max_possible)
            if new_market_booked != ship["market_booked_teu"]:
                ship["market_booked_teu"] = new_market_booked
                updated = True
    if updated:
        save_ships_data(ships_data)
        print("✅ 市場需求已更新")


def init_market_simulation():
    apply_market_simulation()


def get_all_ships_summary(route_key):
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    summary = []
    for ship in route_data:
        remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship.get("user_booked_teu", 0)
        if remaining < 0:
            remaining = 0
        utilization = round((ship["capacity_teu"] - remaining) / ship["capacity_teu"] * 100, 1) if ship["capacity_teu"] > 0 else 0
        summary.append({
            "voyage_no": ship["voyage_no"],
            "ship_name": ship["ship_name"],
            "sailing_date": ship["sailing_date"],
            "sailing_day": ship["sailing_day"],
            "capacity": ship["capacity_teu"],
            "remaining": remaining,
            "utilization": utilization,
            "market_booked": ship["market_booked_teu"],
            "user_booked": ship.get("user_booked_teu", 0),
            "eta_port": ship.get("eta_port", ""),
            "eta_time": ship.get("eta_time", ""),
            "cutoff_time": ship.get("cutoff_time", ""),
            "dynamic_price": calculate_dynamic_price(12000, utilization),
            "port_congestion": get_port_congestion(ship.get("eta_port", route_key[:3]))
        })
    return summary


def get_available_capacity(route_key, cargo_type="normal"):
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    total = 0
    for ship in route_data:
        remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship.get("user_booked_teu", 0)
        if remaining < 0:
            remaining = 0
        total += remaining
    return total


def get_total_capacity(route_key):
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    return sum(s.get("capacity_teu", 0) for s in route_data)


def get_route_summary():
    ships_data = load_ships_data()
    summary = {}
    for rk, rd in ships_data.items():
        total_cap = sum(s["capacity_teu"] for s in rd.get("ships", []))
        total_rem = 0
        for s in rd.get("ships", []):
            rem = s["capacity_teu"] - s["market_booked_teu"] - s.get("user_booked_teu", 0)
            if rem < 0:
                rem = 0
            total_rem += rem
        summary[rk] = {
            "route_name": rd.get("route_name", rk),
            "total_capacity": total_cap,
            "available_capacity": total_rem,
            "utilization": round((total_cap - total_rem) / total_cap * 100, 1) if total_cap > 0 else 0
        }
    return summary


def get_customer_bookings(company_name=None):
    bookings = load_bookings()
    if company_name:
        return [b for b in bookings if b.get("company_name") == company_name]
    return bookings


def get_upcoming_ships(days_ahead=30):
    ships_data = load_ships_data()
    all_ships = []
    today = datetime.now().date()
    for rk, rd in ships_data.items():
        for ship in rd.get("ships", []):
            try:
                sd = datetime.strptime(ship["sailing_date"], "%Y-%m-%d").date()
                days_until = (sd - today).days
                if 0 <= days_until <= days_ahead:
                    remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship.get("user_booked_teu", 0)
                    if remaining < 0:
                        remaining = 0
                    all_ships.append({
                        "route_key": rk,
                        "sailing_date": ship["sailing_date"],
                        "remaining": remaining,
                        "capacity": ship["capacity_teu"]
                    })
            except:
                continue
    return sorted(all_ships, key=lambda x: x["sailing_date"])


def get_booking_summary():
    bookings = load_bookings()
    total_bookings = len(bookings)
    total_containers = sum(b.get("containers", 0) for b in bookings)
    total_revenue = sum(b.get("total_price", 0) for b in bookings)
    cargo_stats = {"normal": 0, "reefer": 0, "dangerous": 0}
    for b in bookings:
        ct = b.get("cargo_type", "normal")
        cargo_stats[ct] = cargo_stats.get(ct, 0) + b.get("containers", 0)
    return {
        "total_bookings": total_bookings,
        "total_containers": total_containers,
        "total_revenue": total_revenue,
        "cargo_stats": cargo_stats
    }


def book_capacity(route_key, sailing_date, containers, company_name, cargo_type="normal", contact_person="", phone=""):
    with _booking_lock:
        ships_data = load_ships_data()
        
        target_ship = None
        target_route_name = None
        for rk, rd in ships_data.items():
            for ship in rd.get("ships", []):
                if ship["sailing_date"] == sailing_date:
                    target_ship = ship
                    target_route_name = rd.get("route_name", rk)
                    break
            if target_ship:
                break
        
        if not target_ship:
            return {"success": False, "error": f"找不到 {sailing_date} 的船班"}
        
        cutoff_time = target_ship.get("cutoff_time", "")
        if cutoff_time:
            try:
                cutoff_dt = datetime.strptime(cutoff_time, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > cutoff_dt:
                    return {"success": False, "error": f"已超過訂艙截止時間 {cutoff_time}"}
            except:
                pass
        
        current_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship.get("user_booked_teu", 0)
        if current_remaining < 0:
            current_remaining = 0
        
        if containers <= 0:
            return {"success": False, "error": "訂艙數量必須大於 0"}
        
        if containers > current_remaining:
            return {
                "success": False,
                "error": f"艙位不足！剩餘 {current_remaining} TEU，需要 {containers} TEU",
                "remaining": current_remaining
            }
        
        target_ship["user_booked_teu"] = target_ship.get("user_booked_teu", 0) + containers
        
        new_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship["user_booked_teu"]
        if new_remaining < 0:
            new_remaining = 0
        
        utilization = round((target_ship["capacity_teu"] - new_remaining) / target_ship["capacity_teu"] * 100, 1)
        dynamic_price = calculate_dynamic_price(12000, utilization)
        
        save_ships_data(ships_data)
        
        booking = {
            "booking_id": f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "booking_time": datetime.now().isoformat(),
            "company_name": company_name,
            "contact_person": contact_person,
            "phone": phone,
            "route_key": rk,
            "route_name": target_route_name,
            "sailing_date": sailing_date,
            "sailing_day": target_ship.get("sailing_day", ""),
            "voyage_no": target_ship.get("voyage_no", ""),
            "ship_name": target_ship.get("ship_name", ""),
            "containers": containers,
            "cargo_type": cargo_type,
            "unit_price": dynamic_price,
            "total_price": dynamic_price * containers,
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
            "ship_name": target_ship.get("ship_name", "立昌輪"),
            "voyage_no": target_ship.get("voyage_no", ""),
            "sailing_date": sailing_date,
            "sailing_day": target_ship.get("sailing_day", ""),
            "containers": containers,
            "cargo_type": cargo_type,
            "remaining": new_remaining,
            "capacity": target_ship["capacity_teu"],
            "utilization": utilization,
            "unit_price": dynamic_price,
            "total_price": dynamic_price * containers,
            "eta_port": target_ship.get("eta_port", ""),
            "eta_time": target_ship.get("eta_time", "航行中"),
            "port_congestion": "順暢",
            "message": f"成功預訂 {containers} TEU，剩餘 {new_remaining} TEU"
        }