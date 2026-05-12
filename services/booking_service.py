"""
艙位訂票系統 - 完整船期管理 + 客戶訂票記錄
支援：市場波動、Cut-off時間、艙位鎖定、多艙等、動態運價
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


def apply_market_simulation():
    """應用市場模擬，更新各船班 market_booked_teu"""
    ships_data = load_ships_data()
    updated = False
    
    for route_key, route_data in ships_data.items():
        for ship in route_data.get("ships", []):
            sailing_date = ship["sailing_date"]
            
            # 只更新未來的船班
            if sailing_date < datetime.now().strftime("%Y-%m-%d"):
                continue
            
            # 根據市場模擬計算新的市場預訂量
            market_demand = get_market_booking_rate(sailing_date)
            
            # 限制不超過容量
            new_market_booked = min(market_demand, ship["capacity_teu"] - ship["user_booked_teu"])
            
            if new_market_booked != ship["market_booked_teu"]:
                ship["market_booked_teu"] = new_market_booked
                updated = True
    
    if updated:
        save_ships_data(ships_data)
        print("✅ 市場需求已更新")


def init_market_simulation():
    """初始化市場模擬（啟動時呼叫）"""
    apply_market_simulation()


def get_all_ships_summary(route_key: str):
    """取得所有船班艙位摘要（含動態運價、港口壅塞）"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    
    summary = []
    for ship in route_data:
        remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
        utilization = round((ship["capacity_teu"] - remaining) / ship["capacity_teu"] * 100, 1)
        
        # 檢查是否超過 Cut-off 時間
        cutoff_time = ship.get("cutoff_time", "")
        is_cutoff_passed = False
        if cutoff_time:
            cutoff_dt = datetime.strptime(cutoff_time, "%Y-%m-%d %H:%M:%S")
            is_cutoff_passed = datetime.now() > cutoff_dt
        
        # 動態運價
        base_price = 12000
        dynamic_price = calculate_dynamic_price(base_price, utilization)
        
        # 港口壅塞資訊
        port_congestion = get_port_congestion(ship.get("eta_port", route_key[:3]))
        
        summary.append({
            "voyage_no": ship["voyage_no"],
            "ship_name": ship["ship_name"],
            "sailing_date": ship["sailing_date"],
            "sailing_day": ship["sailing_day"],
            "capacity": ship["capacity_teu"],
            "reefer_capacity": ship.get("reefer_capacity", 0),
            "dangerous_capacity": ship.get("dangerous_capacity", 0),
            "market_booked": ship["market_booked_teu"],
            "user_booked": ship["user_booked_teu"],
            "remaining": remaining,
            "utilization": utilization,
            "eta_port": ship.get("eta_port", ""),
            "eta_time": ship.get("eta_time", ""),
            "cutoff_time": cutoff_time,
            "is_cutoff_passed": is_cutoff_passed,
            "base_price": base_price,
            "dynamic_price": dynamic_price,
            "port_congestion": port_congestion
        })
    
    return summary


def get_available_capacity(route_key: str, cargo_type: str = "normal") -> int:
    """根據貨物類型取得可用艙位"""
    ships_data = load_ships_data()
    route_data = ships_data.get(route_key, {}).get("ships", [])
    
    total_remaining = 0
    for ship in route_data:
        if cargo_type == "reefer":
            remaining = ship.get("reefer_capacity", 0) - ship.get("reefer_booked", 0)
        elif cargo_type == "dangerous":
            remaining = ship.get("dangerous_capacity", 0) - ship.get("dangerous_booked", 0)
        else:
            remaining = ship["capacity_teu"] - ship["market_booked_teu"] - ship["user_booked_teu"]
        total_remaining += max(0, remaining)
    
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
    total_revenue = sum(b.get("total_price", 0) for b in bookings)
    
    # 各貨物類型統計
    cargo_stats = {"normal": 0, "reefer": 0, "dangerous": 0}
    for b in bookings:
        cargo_type = b.get("cargo_type", "normal")
        cargo_stats[cargo_type] = cargo_stats.get(cargo_type, 0) + b.get("containers", 0)
    
    return {
        "total_bookings": total_bookings,
        "total_containers": total_containers,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "cargo_stats": cargo_stats,
        "recent_bookings": bookings[-10:] if bookings else []
    }


def book_capacity(route_key: str, sailing_date: str, containers: int, company_name: str, 
                  cargo_type: str = "normal", contact_person: str = "", phone: str = "") -> dict:
    """
    預訂艙位 - 動態減少艙位（含鎖定機制）
    """
    with _booking_lock:
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
        
        # 檢查 Cut-off 時間
        cutoff_time = target_ship.get("cutoff_time", "")
        if cutoff_time:
            cutoff_dt = datetime.strptime(cutoff_time, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > cutoff_dt:
                return {"success": False, "error": f"已超過訂艙截止時間 {cutoff_time}"}
        
        # 根據貨物類型計算可用艙位
        if cargo_type == "reefer":
            current_remaining = target_ship.get("reefer_capacity", 0) - target_ship.get("reefer_booked", 0)
            capacity_key = "reefer_capacity"
            booked_key = "reefer_booked"
        elif cargo_type == "dangerous":
            current_remaining = target_ship.get("dangerous_capacity", 0) - target_ship.get("dangerous_booked", 0)
            capacity_key = "dangerous_capacity"
            booked_key = "dangerous_booked"
        else:
            current_remaining = target_ship["capacity_teu"] - target_ship["market_booked_teu"] - target_ship["user_booked_teu"]
            capacity_key = "capacity_teu"
            booked_key = "user_booked_teu"
        
        if containers > current_remaining:
            return {
                "success": False, 
                "error": f"{'冷藏' if cargo_type=='reefer' else '危險品' if cargo_type=='dangerous' else '一般'}艙位不足！剩餘 {current_remaining} TEU，需要 {containers} TEU",
                "remaining": current_remaining
            }
        
        # 更新預訂量
        target_ship[booked_key] = target_ship.get(booked_key, 0) + containers
        save_ships_data(ships_data)
        
        new_remaining = current_remaining - containers
        utilization = round((target_ship[capacity_key] - new_remaining) / target_ship[capacity_key] * 100, 1) if target_ship[capacity_key] > 0 else 0
        dynamic_price = calculate_dynamic_price(12000, utilization)
        
        # 港口壅塞影響 ETA
        port_congestion = get_port_congestion(target_ship.get("eta_port", route_key[:3]))
        eta_time = target_ship.get("eta_time", "")
        if port_congestion["delay_hours"] > 0 and eta_time:
            eta_dt = datetime.strptime(eta_time, "%Y-%m-%d %H:%M:%S")
            new_eta = eta_dt.replace(hour=eta_dt.hour + int(port_congestion["delay_hours"]))
            eta_time = new_eta.strftime("%Y-%m-%d %H:%M:%S")
        
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
            "cargo_type": cargo_type,
            "unit_price": dynamic_price,
            "total_price": dynamic_price * containers,
            "eta_port": target_ship.get("eta_port", ""),
            "eta_time": eta_time,
            "status": "confirmed",
            "port_congestion": port_congestion["message"]
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
            "cargo_type": cargo_type,
            "remaining": new_remaining,
            "capacity": target_ship[capacity_key],
            "utilization": utilization,
            "unit_price": dynamic_price,
            "total_price": dynamic_price * containers,
            "eta_port": target_ship.get("eta_port", ""),
            "eta_time": eta_time,
            "port_congestion": port_congestion["message"],
            "message": f"成功預訂 {containers} TEU，剩餘 {new_remaining} TEU"
        }


def get_booking_by_id(booking_id: str):
    """根據訂位編號查詢訂票"""
    bookings = load_bookings()
    for booking in bookings:
        if booking.get("booking_id") == booking_id:
            return booking
    return None


def cancel_booking(booking_id: str) -> dict:
    """取消訂位（歸還艙位）"""
    with _booking_lock:
        bookings = load_bookings()
        booking = None
        booking_index = -1
        for i, b in enumerate(bookings):
            if b.get("booking_id") == booking_id:
                booking = b
                booking_index = i
                break
        
        if not booking:
            return {"success": False, "error": "找不到該訂位記錄"}
        
        # 歸還艙位
        ships_data = load_ships_data()
        route_data = ships_data.get(booking["route_key"], {})
        for ship in route_data.get("ships", []):
            if ship["sailing_date"] == booking["sailing_date"]:
                cargo_type = booking.get("cargo_type", "normal")
                if cargo_type == "reefer":
                    ship["reefer_booked"] = ship.get("reefer_booked", 0) - booking["containers"]
                elif cargo_type == "dangerous":
                    ship["dangerous_booked"] = ship.get("dangerous_booked", 0) - booking["containers"]
                else:
                    ship["user_booked_teu"] -= booking["containers"]
                break
        
        save_ships_data(ships_data)
        
        # 刪除訂票記錄
        bookings.pop(booking_index)
        save_bookings(bookings)
        
        return {"success": True, "message": f"已取消訂位 {booking_id}"}