"""
艙位訂票系統 - 完整船期管理 + 客戶訂票記錄
支援動態艙位減少、混合運輸推薦
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from config import DATA_DIR

SHIPS_FILE = DATA_DIR / "ships_schedule.json"
BOOKING_FILE = DATA_DIR / "bookings.json"
CUSTOMER_FILE = DATA_DIR / "customers.json"


def load_ships_data():
    """載入船舶艙位資料"""
    if not SHIPS_FILE.exists():
        return {}
    try:
        with open(SHIPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_ships_data(ships_data):
    """儲存船舶艙位資料"""
    with open(SHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(ships_data, f, ensure_ascii=False, indent=2)


def load_bookings():
    """載入訂票記錄"""
    if not BOOKING_FILE.exists():
        return []
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_bookings(bookings):
    """儲存訂票記錄"""
    with open(BOOKING_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


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
            "eta_time": ship.get("eta_time", "")
        })
    
    return summary


def book_capacity(route_key: str, sailing_date: str, containers: int, company_name: str, contact_person: str = "", phone: str = "") -> dict:
    """
    預訂艙位 - 動態減少艙位
    """
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
            "remaining": current_remaining,
            "available": current_remaining
        }
    
    # 更新 user_booked_teu (動態減少)
    target_ship["user_booked_teu"] += containers
    
    # 儲存更新後的資料
    save_ships_data(ships_data)
    
    new_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship["user_booked_teu"]
    utilization = round((target_ship["capacity_teu"] - new_remaining) / target_ship["capacity_teu"] * 100, 1)
    
    # 記錄訂票
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