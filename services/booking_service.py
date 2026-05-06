"""
艙位訂票系統 - 模擬航空/航運訂位系統
總艙位：1700 TEU
剩餘艙位：約 1/3 (動態計算)
"""

import json
from datetime import datetime
from pathlib import Path
from config import DATA_DIR

BOOKING_FILE = DATA_DIR / "bookings.json"

# 航線艙位配置（總艙位 1700 TEU）
ROUTE_CAPACITY = {
    "KHH-TXG": {"total": 850, "route_name": "高雄港 → 台中港", "price": 12000},
    "TXG-KHH": {"total": 850, "route_name": "台中港 → 高雄港", "price": 12000},
}

# 貨櫃類型對應的艙位消耗
CONTAINER_TYPE_FACTOR = {
    "normal": 1.0,      # 一般貨櫃 1 TEU
    "special": 1.2,     # 危險品/特殊貨 1.2 TEU
}

# 初始剩餘艙位（總艙位的 1/3，約 566 TEU）
INITIAL_REMAINING = {
    "KHH-TXG": 283,  # 850 的 1/3 約 283
    "TXG-KHH": 283,  # 850 的 1/3 約 283
}


def load_bookings():
    """載入訂票記錄"""
    if not BOOKING_FILE.exists():
        return {}
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_bookings(bookings):
    """儲存訂票記錄"""
    BOOKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKING_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


def get_available_capacity(route_key: str) -> int:
    """取得指定航線可用艙位"""
    bookings = load_bookings()
    total = ROUTE_CAPACITY.get(route_key, {}).get("total", 850)
    
    # 計算已預訂的艙位
    booked = 0
    for booking in bookings.get(route_key, []):
        booked += booking.get("feu_used", 0)
    
    # 初始剩餘艙位（總艙位的 1/3）
    initial_remaining = INITIAL_REMAINING.get(route_key, total // 3)
    
    # 實際剩餘 = 初始剩餘 - 已預訂
    remaining = max(0, initial_remaining - booked)
    return int(remaining)


def get_total_capacity(route_key: str) -> int:
    """取得航線總艙位"""
    return ROUTE_CAPACITY.get(route_key, {}).get("total", 850)


def book_capacity(route_key: str, containers: int, container_type: str = "normal", company_name: str = "") -> dict:
    """
    預訂艙位
    
    參數:
        route_key: 航線代碼 (如 KHH-TXG)
        containers: 貨櫃數量 (FEU)
        container_type: 貨櫃類型 (normal/special)
        company_name: 公司名稱
    
    返回:
        dict: 訂票結果
    """
    available = get_available_capacity(route_key)
    feu_needed = containers * CONTAINER_TYPE_FACTOR.get(container_type, 1.0)
    
    if feu_needed > available:
        return {
            "success": False, 
            "error": f"艙位不足！剩餘 {available} TEU，需要 {feu_needed:.1f} TEU",
            "available": available,
            "needed": round(feu_needed, 1)
        }
    
    # 載入現有訂票記錄
    bookings = load_bookings()
    if route_key not in bookings:
        bookings[route_key] = []
    
    # 建立新訂票記錄
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
    
    # 計算剩餘艙位
    remaining = available - feu_needed
    total = get_total_capacity(route_key)
    
    return {
        "success": True,
        "booking_id": booking["id"],
        "feu_used": round(feu_needed, 1),
        "remaining": int(remaining),
        "total": total,
        "route_name": ROUTE_CAPACITY.get(route_key, {}).get("route_name", route_key),
        "message": f"成功預訂 {containers} FEU，剩餘艙位 {int(remaining)} TEU"
    }


def cancel_booking(route_key: str, booking_id: str) -> dict:
    """取消訂位"""
    bookings = load_bookings()
    if route_key not in bookings:
        return {"success": False, "error": "找不到該航線訂位記錄"}
    
    for i, booking in enumerate(bookings[route_key]):
        if booking["id"] == booking_id:
            removed = bookings[route_key].pop(i)
            save_bookings(bookings)
            return {
                "success": True, 
                "canceled": removed,
                "message": f"已取消訂位 {booking_id}"
            }
    
    return {"success": False, "error": "找不到該訂位編號"}


def get_route_summary():
    """取得所有航線艙位摘要"""
    summary = {}
    for route_key, info in ROUTE_CAPACITY.items():
        available = get_available_capacity(route_key)
        total = info["total"]
        initial = INITIAL_REMAINING.get(route_key, total // 3)
        booked = initial - available
        
        summary[route_key] = {
            "route_name": info["route_name"],
            "total": total,
            "initial_remaining": initial,
            "available": available,
            "booked": booked,
            "utilization": round((total - available) / total * 100, 1),
        }
    return summary


def get_all_bookings():
    """取得所有訂票記錄"""
    return load_bookings()


def reset_capacity():
    """重置艙位（用於測試）"""
    save_bookings({})
    return {"success": True, "message": "艙位已重置"}


# 測試用
if __name__ == "__main__":
    print("=== 艙位訂票系統測試 ===")
    print(f"高雄→台中 可用艙位: {get_available_capacity('KHH-TXG')} TEU")
    print(f"台中→高雄 可用艙位: {get_available_capacity('TXG-KHH')} TEU")
    
    result = book_capacity("KHH-TXG", 50, "normal", "測試公司")
    print(f"訂票結果: {result}")
    
    print(f"訂票後可用艙位: {get_available_capacity('KHH-TXG')} TEU")
    print(f"航線摘要: {get_route_summary()}")