import random
from datetime import datetime

def get_market_booking_rate(sailing_date):
    date_obj = datetime.strptime(sailing_date, "%Y-%m-%d")
    weekday = date_obj.weekday()
    day_of_month = date_obj.day
    base_demand = 200
    if weekday == 4: weekday_factor = 1.8
    elif weekday == 5: weekday_factor = 1.5
    else: weekday_factor = 1.0
    if day_of_month >= 25: month_end_factor = 1.6
    elif day_of_month >= 20: month_end_factor = 1.3
    else: month_end_factor = 1.0
    return int(base_demand * weekday_factor * month_end_factor * random.uniform(0.8, 1.2))

def get_port_congestion(port_code):
    hour = datetime.now().hour
    if datetime.now().weekday() == 4 and 14 <= hour <= 19:
        return {"level": "HIGH", "delay_hours": random.uniform(4, 12), "message": f"{port_code} 嚴重壅塞，預計延誤 {random.uniform(4,12):.1f} 小時"}
    elif 8 <= hour <= 10:
        return {"level": "MEDIUM", "delay_hours": random.uniform(1, 4), "message": f"{port_code} 略為繁忙"}
    return {"level": "LOW", "delay_hours": 0, "message": f"{port_code} 順暢"}

def calculate_dynamic_price(base_price, utilization):
    if utilization >= 95: return int(base_price * 2.5)
    if utilization >= 90: return int(base_price * 2.0)
    if utilization >= 80: return int(base_price * 1.5)
    if utilization >= 70: return int(base_price * 1.2)
    return base_price