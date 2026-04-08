"""
智慧貨櫃調度決策引擎 - AI 多因子評分模型
功能：
1. 公路即時車流判斷（TDX API）
2. 船期/港口時機判斷
3. 多因子評分模型（取代 if-else）
4. 自動貨櫃轉移決策
"""

import random
from datetime import datetime
import math

# ================= 港口資料（模擬 iMarine） =================
PORT_DATA = {
    "KHH": {
        "name": "高雄港",
        "lat": 22.616,
        "lon": 120.3,
        "schedules": [
            {"time": "08:00", "destination": "新加坡", "capacity": 200},
            {"time": "14:00", "destination": "香港", "capacity": 150},
            {"time": "20:00", "destination": "洛杉磯", "capacity": 300},
        ]
    },
    "TXG": {
        "name": "台中港",
        "lat": 24.27,
        "lon": 120.52,
        "schedules": [
            {"time": "10:00", "destination": "廈門", "capacity": 100},
            {"time": "16:00", "destination": "東京", "capacity": 120},
        ]
    },
    "KEL": {
        "name": "基隆港",
        "lat": 25.15,
        "lon": 121.75,
        "schedules": [
            {"time": "09:00", "destination": "上海", "capacity": 180},
            {"time": "15:00", "destination": "首爾", "capacity": 140},
            {"time": "22:00", "destination": "西雅圖", "capacity": 250},
        ]
    },
    "TPE": {
        "name": "台北港",
        "lat": 25.15,
        "lon": 121.38,
        "schedules": [
            {"time": "11:00", "destination": "福州", "capacity": 80},
            {"time": "17:00", "destination": "大阪", "capacity": 100},
        ]
    },
    "HUN": {
        "name": "花蓮港",
        "lat": 23.98,
        "lon": 121.62,
        "schedules": [
            {"time": "13:00", "destination": "那霸", "capacity": 60},
        ]
    }
}


# ================= 1. 船期模擬（可接真實 AIS） =================
def get_ship_schedule(port_code="KHH"):
    """
    獲取港口船期資訊
    
    真實資料來源：
    - iMarine 航港資料庫
    - MarineTraffic AIS API
    - 臺灣港務公司 API
    
    目前使用固定 JSON 資料 + 模擬即時狀態
    """
    port_info = PORT_DATA.get(port_code, PORT_DATA["KHH"])
    
    # 找出下一班船
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    current_time = current_hour + current_minute / 60
    
    next_ship = None
    min_wait = 24
    
    for ship in port_info["schedules"]:
        ship_hour = int(ship["time"].split(":")[0])
        ship_minute = int(ship["time"].split(":")[1])
        ship_time = ship_hour + ship_minute / 60
        
        wait = ship_time - current_time
        if wait < 0:
            wait += 24
        
        if wait < min_wait:
            min_wait = wait
            next_ship = ship
    
    arrival_hours = round(min_wait, 1)
    
    # 根據到達時間決定狀態
    if arrival_hours <= 3:
        status = "🟢 立即到港"
        urgency = "high"
    elif arrival_hours <= 8:
        status = "🟡 即將到港"
        urgency = "medium"
    elif arrival_hours <= 16:
        status = "⏳ 正常"
        urgency = "low"
    else:
        status = "🔴 尚需等待"
        urgency = "very_low"
    
    # 模擬即時艙位（根據預定容量調整）
    import random
    available_capacity = max(0, next_ship["capacity"] - random.randint(0, 50))
    
    return {
        "port": port_code,
        "port_name": port_info["name"],
        "next_ship_in_hours": arrival_hours,
        "next_ship_in_minutes": arrival_hours * 60,
        "next_destination": next_ship["destination"],
        "status": status,
        "urgency": urgency,
        "available_capacity": available_capacity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "iMarine 模擬資料"
    }


# ================= 2. AI 多因子評分模型 =================
def calculate_scores(road_data, ship_data, cargo):
    """
    多因子評分模型 - 計算海運和公路的綜合分數
    
    評分因子：
    - 公路壅塞程度 (權重 3)
    - 船期緊急程度 (權重 3)
    - 貨物時效敏感度 (權重 5)
    - 碳排放效益 (權重 2)
    - 成本節省 (權重 2)
    
    返回:
        score_sea: 海運分數 (0-10)
        score_road: 公路分數 (0-10)
    """
    score_sea = 0
    score_road = 0
    
    # 因子1: 公路壅塞程度 (壅塞越嚴重，海運分數越高)
    congestion_scores = {"low": 0, "medium": 2, "high": 5}
    score_sea += congestion_scores.get(road_data.get("level", "low"), 0) * 0.6
    
    # 因子2: 船期緊急程度 (船越快來，海運分數越高)
    urgency_scores = {"high": 5, "medium": 3, "low": 1, "very_low": 0}
    score_sea += urgency_scores.get(ship_data.get("urgency", "low"), 0) * 0.6
    
    # 因子3: 貨物時效敏感度 (時效要求越高，公路分數越高)
    time_sensitivity = cargo.get("time_sensitivity", 0.3)
    score_road += time_sensitivity * 5  # 最高 5 分
    
    # 因子4: 碳排放效益 (海運碳排較低，加分)
    score_sea += 2  # 基礎碳排優勢
    
    # 因子5: 成本效益 (海運成本較低，加分)
    score_sea += 1.5
    
    # 正規化到 0-10 分
    score_sea = min(10, score_sea)
    score_road = min(10, score_road)
    
    return round(score_sea, 1), round(score_road, 1)


def calculate_transfer_ratio(score_sea, score_road):
    """
    根據分數計算轉移比例
    
    公式: ratio = score_sea / (score_sea + score_road)
    """
    total = score_sea + score_road
    if total == 0:
        return 0.5
    
    ratio = score_sea / total
    # 限制在 20% - 80% 之間，避免極端值
    return max(0.2, min(0.8, ratio))


# ================= 3. 碳排放比較計算 =================
def calculate_carbon_impact(containers, distance_km, mode, emission_factor):
    """計算特定模式的碳排放"""
    return containers * distance_km * emission_factor


def compare_carbon_saving(containers, distance_km, road_factor, sea_factor):
    """比較轉移後的碳排節省量"""
    road_carbon = containers * distance_km * road_factor
    sea_carbon = containers * distance_km * sea_factor
    saved = road_carbon - sea_carbon
    saved_pct = (saved / road_carbon) * 100 if road_carbon > 0 else 0
    return {
        "road_carbon": round(road_carbon, 2),
        "sea_carbon": round(sea_carbon, 2),
        "saved": round(saved, 2),
        "saved_pct": round(saved_pct, 1)
    }


# ================= 4. 智慧調度核心決策（AI 評分模型） =================
def smart_dispatch(containers, distance_km, road_data, ship_data, cargo):
    """
    智慧貨櫃調度決策引擎 - AI 多因子評分模型
    
    決策流程：
    1. 計算海運和公路的綜合分數
    2. 根據分數比例計算轉移比例
    3. 分配貨櫃
    4. 計算碳排效益
    """
    
    # 🔥 AI 多因子評分
    score_sea, score_road = calculate_scores(road_data, ship_data, cargo)
    
    # 計算轉移比例
    transfer_ratio = calculate_transfer_ratio(score_sea, score_road)
    
    # 分配貨櫃
    to_sea = int(containers * transfer_ratio)
    to_road = containers - to_sea
    
    # 確保不超過艙位容量
    if ship_data.get("available_capacity", 9999) < to_sea:
        to_sea = ship_data["available_capacity"]
        to_road = containers - to_sea
    
    # 產生決策原因
    reason_parts = []
    
    if road_data.get("level") == "high":
        reason_parts.append(f"公路壅塞（時速 {road_data['avg_speed']} km/h）")
    elif road_data.get("level") == "medium":
        reason_parts.append(f"公路車多（時速 {road_data['avg_speed']} km/h）")
    
    if ship_data.get("urgency") == "high":
        reason_parts.append(f"船舶 {ship_data['next_ship_in_hours']} 小時內到港")
    elif ship_data.get("urgency") == "medium":
        reason_parts.append(f"船舶即將到港")
    
    if cargo.get("time_sensitivity", 0) > 0.7:
        reason_parts.append(f"貨物時效性高（敏感度 {cargo['time_sensitivity']*100:.0f}%）")
    
    if transfer_ratio > 0.6:
        reason = f"AI 評分模型推薦轉海運（海運分數 {score_sea} / 公路分數 {score_road}）"
        if reason_parts:
            reason += f"：{', '.join(reason_parts)}"
        suggested_action = "transfer_to_sea"
    elif transfer_ratio < 0.4:
        reason = f"AI 評分模型推薦保留公路（海運分數 {score_sea} / 公路分數 {score_road}）"
        if reason_parts:
            reason += f"：{', '.join(reason_parts)}"
        suggested_action = "keep_road"
    else:
        reason = f"AI 評分模型建議平衡分配（海運分數 {score_sea} / 公路分數 {score_road}）"
        if reason_parts:
            reason += f"：{', '.join(reason_parts)}"
        suggested_action = "balanced"
    
    decision = {
        "to_sea": to_sea,
        "to_road": to_road,
        "transfer_ratio": round(transfer_ratio * 100, 1),
        "score_sea": score_sea,
        "score_road": score_road,
        "reason": reason,
        "suggested_action": suggested_action,
        "carbon_benefit": None
    }
    
    # 計算碳排效益
    if to_sea > 0:
        decision["carbon_benefit"] = compare_carbon_saving(
            to_sea, distance_km, 0.06, 0.02
        )
    
    return decision


# ================= 測試用 =================
if __name__ == "__main__":
    print("=== AI 多因子評分模型測試 ===\n")
    
    # 測試不同情境
    test_cases = [
        {
            "name": "情境1: 公路壅塞 + 船期緊急",
            "road": {"level": "high", "avg_speed": 25, "level_text": "🔴 壅塞"},
            "ship": {"urgency": "high", "next_ship_in_hours": 2, "available_capacity": 200},
            "cargo": {"time_sensitivity": 0.3}
        },
        {
            "name": "情境2: 公路順暢 + 船期正常",
            "road": {"level": "low", "avg_speed": 75, "level_text": "🟢 順暢"},
            "ship": {"urgency": "low", "next_ship_in_hours": 12, "available_capacity": 150},
            "cargo": {"time_sensitivity": 0.3}
        },
        {
            "name": "情境3: 高時效貨物 + 公路順暢",
            "road": {"level": "low", "avg_speed": 75, "level_text": "🟢 順暢"},
            "ship": {"urgency": "medium", "next_ship_in_hours": 5, "available_capacity": 180},
            "cargo": {"time_sensitivity": 0.9}
        },
        {
            "name": "情境4: 公路壅塞 + 高時效貨物（衝突）",
            "road": {"level": "high", "avg_speed": 20, "level_text": "🔴 壅塞"},
            "ship": {"urgency": "low", "next_ship_in_hours": 10, "available_capacity": 120},
            "cargo": {"time_sensitivity": 0.85}
        }
    ]
    
    for test in test_cases:
        print(f"📌 {test['name']}")
        print(f"   公路: {test['road']['level_text']} (時速 {test['road']['avg_speed']} km/h)")
        print(f"   船舶: {test['ship']['urgency']} ( {test['ship']['next_ship_in_hours']} 小時後)")
        print(f"   貨物: 時效敏感度 {test['cargo']['time_sensitivity']*100:.0f}%")
        
        score_sea, score_road = calculate_scores(test['road'], test['ship'], test['cargo'])
        ratio = calculate_transfer_ratio(score_sea, score_road)
        
        print(f"   🧠 AI 評分: 海運 {score_sea} / 公路 {score_road}")
        print(f"   📊 轉移比例: {ratio*100:.0f}% 海運 / {(1-ratio)*100:.0f}% 公路")
        print()