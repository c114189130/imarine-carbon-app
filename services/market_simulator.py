import random
from datetime import datetime

def get_market_booking_rate(sailing_date: str) -> int:
    date_obj = datetime.strptime(sailing_date, "%Y-%m-%d")
    weekday = date_obj.weekday()
    day_of_month = date_obj.day
    
    base_demand = 200
    if weekday == 4:
        weekday_factor = 1.8
    elif weekday == 5:
        weekday_factor = 1.5
    else:
        weekday_factor = 1.0
    
    if day_of_month >= 25:
        month_end_factor = 1.6
    elif day_of_month >= 20:
        month_end_factor = 1.3
    else:
        month_end_factor = 1.0
    
    random_factor = random.uniform(0.8, 1.2)
    return int(base_demand * weekday_factor * month_end_factor * random_factor)

def get_port_congestion(port_code: str) -> dict:
    hour = datetime.now().hour
    if datetime.now().weekday() == 4 and 14 <= hour <= 19:
        delay_hours = random.uniform(4, 12)
        level = "HIGH"
    elif 8 <= hour <= 10:
        delay_hours = random.uniform(1, 4)
        level = "MEDIUM"
    else:
        delay_hours = random.uniform(0, 1)
        level = "LOW"
    
    return {
        "level": level,
        "delay_hours": round(delay_hours, 1),
        "message": f"{port_code} 目前{'嚴重壅塞' if level == 'HIGH' else '略為繁忙' if level == 'MEDIUM' else '順暢'}，預計延誤 {delay_hours:.1f} 小時"
    }

def calculate_dynamic_price(base_price: int, utilization: float) -> int:
    if utilization >= 95:
        multiplier = 2.5
    elif utilization >= 90:
        multiplier = 2.0
    elif utilization >= 80:
        multiplier = 1.5
    elif utilization >= 70:
        multiplier = 1.2
    else:
        multiplier = 1.0
    return int(base_price * multiplier)