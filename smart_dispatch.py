"""
智慧貨櫃調度決策引擎 - AI 多因子評分模型
"""

import random
from datetime import datetime

# 港口資料（模擬 iMarine）
PORT_DATA = {
    "KHH": {"name": "高雄港", "schedules": [{"time": "08:00", "destination": "新加坡", "capacity": 200}, {"time": "14:00", "destination": "香港", "capacity": 150}, {"time": "20:00", "destination": "洛杉磯", "capacity": 300}]},
    "TXG": {"name": "台中港", "schedules": [{"time": "10:00", "destination": "廈門", "capacity": 100}, {"time": "16:00", "destination": "東京", "capacity": 120}]},
    "KEL": {"name": "基隆港", "schedules": [{"time": "09:00", "destination": "上海", "capacity": 180}, {"time": "15:00", "destination": "首爾", "capacity": 140}, {"time": "22:00", "destination": "西雅圖", "capacity": 250}]},
    "TPE": {"name": "台北港", "schedules": [{"time": "11:00", "destination": "福州", "capacity": 80}, {"time": "17:00", "destination": "大阪", "capacity": 100}]},
    "HUN": {"name": "花蓮港", "schedules": [{"time": "13:00", "destination": "那霸", "capacity": 60}]}
}

def get_ship_schedule(port_code="KHH"):
    port_info = PORT_DATA.get(port_code, PORT_DATA["KHH"])
    current_hour = datetime.now().hour + datetime.now().minute / 60
    next_ship = None
    min_wait = 24
    for ship in port_info["schedules"]:
        ship_time = int(ship["time"].split(":")[0]) + int(ship["time"].split(":")[1]) / 60
        wait = ship_time - current_hour
        if wait < 0:
            wait += 24
        if wait < min_wait:
            min_wait = wait
            next_ship = ship
    arrival_hours = round(min_wait, 1)
    if arrival_hours <= 3:
        status, urgency = "🟢 立即到港", "high"
    elif arrival_hours <= 8:
        status, urgency = "🟡 即將到港", "medium"
    elif arrival_hours <= 16:
        status, urgency = "⏳ 正常", "low"
    else:
        status, urgency = "🔴 尚需等待", "very_low"
    return {"port": port_code, "port_name": port_info["name"], "next_ship_in_hours": arrival_hours, "next_destination": next_ship["destination"], "status": status, "urgency": urgency, "available_capacity": max(0, next_ship["capacity"] - random.randint(0, 50)), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": "iMarine 模擬資料"}

def get_road_congestion():
    current_hour = datetime.now().hour
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        level = random.choice(["medium", "high"])
    elif 11 <= current_hour <= 13 or 18 <= current_hour <= 20:
        level = random.choice(["low", "medium", "high"])
    else:
        level = random.choice(["low", "medium"])
    speed_map = {"low": random.randint(60, 90), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
    delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
    text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
    return {"level": level, "level_text": text_map[level], "avg_speed": speed_map[level], "delay_factor": delay_map[level], "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": "模擬資料"}

def calculate_scores(road_data, ship_data, cargo):
    score_sea, score_road = 0, 0
    congestion_scores = {"low": 0, "medium": 2, "high": 5}
    score_sea += congestion_scores.get(road_data.get("level", "low"), 0) * 0.6
    urgency_scores = {"high": 5, "medium": 3, "low": 1, "very_low": 0}
    score_sea += urgency_scores.get(ship_data.get("urgency", "low"), 0) * 0.6
    score_road += cargo.get("time_sensitivity", 0.3) * 5
    score_sea += 2 + 1.5
    return round(min(10, score_sea), 1), round(min(10, score_road), 1)

def calculate_transfer_ratio(score_sea, score_road):
    total = score_sea + score_road
    return max(0.2, min(0.8, score_sea / total if total > 0 else 0.5))

def compare_carbon_saving(containers, distance_km, road_factor, sea_factor):
    road_carbon = containers * distance_km * road_factor
    sea_carbon = containers * distance_km * sea_factor
    saved = road_carbon - sea_carbon
    return {"road_carbon": round(road_carbon, 2), "sea_carbon": round(sea_carbon, 2), "saved": round(saved, 2), "saved_pct": round((saved / road_carbon) * 100, 1) if road_carbon > 0 else 0}

def smart_dispatch(containers, distance_km, road_data, ship_data, cargo):
    score_sea, score_road = calculate_scores(road_data, ship_data, cargo)
    transfer_ratio = calculate_transfer_ratio(score_sea, score_road)
    to_sea = int(containers * transfer_ratio)
    to_road = containers - to_sea
    if ship_data.get("available_capacity", 9999) < to_sea:
        to_sea = ship_data["available_capacity"]
        to_road = containers - to_sea
    reason_parts = []
    if road_data.get("level") == "high":
        reason_parts.append(f"公路壅塞（時速 {road_data['avg_speed']} km/h）")
    elif road_data.get("level") == "medium":
        reason_parts.append(f"公路車多（時速 {road_data['avg_speed']} km/h）")
    if ship_data.get("urgency") in ["high", "medium"]:
        reason_parts.append(f"船舶 {ship_data['next_ship_in_hours']} 小時內到港")
    if cargo.get("time_sensitivity", 0) > 0.7:
        reason_parts.append(f"貨物時效性高（敏感度 {cargo['time_sensitivity']*100:.0f}%）")
    reason = f"AI 評分模型推薦{'轉海運' if transfer_ratio > 0.6 else '保留公路' if transfer_ratio < 0.4 else '平衡分配'}（海運 {score_sea} / 公路 {score_road}）"
    if reason_parts:
        reason += f"：{', '.join(reason_parts)}"
    decision = {"to_sea": to_sea, "to_road": to_road, "transfer_ratio": round(transfer_ratio * 100, 1), "score_sea": score_sea, "score_road": score_road, "reason": reason, "suggested_action": "transfer_to_sea" if transfer_ratio > 0.6 else "keep_road" if transfer_ratio < 0.4 else "balanced"}
    if to_sea > 0:
        decision["carbon_benefit"] = compare_carbon_saving(to_sea, distance_km, 0.06, 0.02)
    return decision