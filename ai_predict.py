import random
from datetime import datetime

def predict_congestion(day_of_week=None, hour=None):
    """預測壅塞程度（基於時段+星期）"""
    if day_of_week is None:
        now = datetime.now()
        day_of_week = now.weekday()
        hour = now.hour

    score = 0.0

    # 平日尖峰
    if day_of_week in [0, 1, 2, 3, 4]:
        if 7 <= hour <= 9:
            score += 0.7  # 早上尖峰
        elif 17 <= hour <= 19:
            score += 0.8  # 晚上尖峰
        elif 10 <= hour <= 16:
            score += 0.2  # 離峰
        else:
            score += 0.1
    else:
        # 假日
        if 10 <= hour <= 20:
            score += 0.5  # 出遊潮
        else:
            score += 0.1

    # 午餐
    if 11 <= hour <= 13:
        score += 0.3

    # 加入隨機誤差
    score += random.uniform(-0.15, 0.15)

    if score > 0.7:
        return "high"
    elif score > 0.35:
        return "medium"
    else:
        return "low"


def predict_accident_risk(road_km, congestion_level):
    """預測事故風險"""
    base_rate = ACCIDENT_RATE["road"] if congestion_level != "low" else ACCIDENT_RATE["road"] * 0.5
    # 壅塞時事故風險增加
    if congestion_level == "high":
        base_rate *= 2.0
    elif congestion_level == "medium":
        base_rate *= 1.3
    # 距離越長風險越高
    risk = base_rate * (road_km / 100)
    return round(risk, 6)


def estimate_transport_time(distance_km, road_speed, congestion_level, ship_data):
    """估算運輸時間"""
    delay = {"low": 1.0, "medium": 1.3, "high": 1.8}
    road_time = (distance_km / road_speed) * delay.get(congestion_level, 1.0)

    wait_hours = ship_data.get("next_ship_hours", 24)
    sea_travel = distance_km / 30  # 海運約 30 km/h
    handling = 4
    sea_time = wait_hours + sea_travel + handling

    return {
        "road_time": round(road_time, 1),
        "sea_time": round(sea_time, 1),
        "road_faster": road_time < sea_time
    }