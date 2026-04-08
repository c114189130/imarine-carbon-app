"""
智慧貨櫃調度決策引擎
功能：
1. 公路即時車流判斷（接入 TDX API）
2. 船期/港口時機判斷（模擬資料，預留 API 接口）
3. AI 多因子評分決策模型
"""

import random
import requests
from datetime import datetime
import json
import os

# ================= TDX API 設定 =================
# 註冊取得：https://tdx.transportdata.tw
TDX_APP_ID = "your_app_id"  # 請替換為你的 App ID
TDX_APP_KEY = "your_app_key"  # 請替換為你的 App Key

# 台灣主要高速公路路段代碼
HIGHWAY_SECTIONS = {
    "national_1_north": {"id": "N1-N", "name": "國道1號(北)", "city": "台北"},
    "national_1_central": {"id": "N1-C", "name": "國道1號(中)", "city": "台中"},
    "national_1_south": {"id": "N1-S", "name": "國道1號(南)", "city": "高雄"},
    "national_3_north": {"id": "N3-N", "name": "國道3號(北)", "city": "台北"},
    "national_3_south": {"id": "N3-S", "name": "國道3號(南)", "city": "高雄"},
}

def get_tdx_token():
    """取得 TDX API 存取令牌"""
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": TDX_APP_ID,
        "client_secret": TDX_APP_KEY
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"TDX token 取得失敗: {response.status_code}")
            return None
    except Exception as e:
        print(f"TDX API 連線錯誤: {e}")
        return None


def get_road_congestion_real(route_id="national_1_central"):
    """
    從 TDX API 獲取真實公路車況
    
    真實 API: https://tdx.transportdata.tw/api/basic/v3/Road/Live/City
    """
    token = get_tdx_token()
    if not token:
        # 如果 API 失敗，回退到模擬數據
        return get_road_congestion_mock()
    
    # 取得路段對應的城市
    section = HIGHWAY_SECTIONS.get(route_id, HIGHWAY_SECTIONS["national_1_central"])
    city = section["city"]
    
    # TDX 即時車況 API
    url = f"https://tdx.transportdata.tw/api/basic/v3/Road/Live/City/{city}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 解析回傳數據，取得平均車速
            if data and len(data) > 0:
                avg_speed = data[0].get("AverageSpeed", 60)
                
                # 根據車速判斷壅塞程度
                if avg_speed >= 60:
                    level = "low"
                    level_text = "🟢 順暢"
                elif avg_speed >= 35:
                    level = "medium"
                    level_text = "🟡 車多"
                else:
                    level = "high"
                    level_text = "🔴 壅塞"
                
                return {
                    "level": level,
                    "level_text": level_text,
                    "avg_speed": avg_speed,
                    "delay_factor": {"low": 1.0, "medium": 1.6, "high": 2.5}[level],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "TDX API"
                }
    except Exception as e:
        print(f"TDX API 呼叫失敗: {e}")
    
    # 回退到模擬數據
    return get_road_congestion_mock()


def get_road_congestion_mock():
    """
    模擬公路車況（API 失敗時的備援）
    """
    current_hour = datetime.now().hour
    
    # 根據時間決定壅塞機率
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        congestion_probs = {"low": 0.2, "medium": 0.4, "high": 0.4}
    elif 11 <= current_hour <= 13 or 18 <= current_hour <= 20:
        congestion_probs = {"low": 0.3, "medium": 0.4, "high": 0.3}
    else:
        congestion_probs = {"low": 0.5, "medium": 0.3, "high": 0.2}
    
    rand = random.random()
    if rand < congestion_probs["low"]:
        level = "low"
    elif rand < congestion_probs["low"] + congestion_probs["medium"]:
        level = "medium"
    else:
        level = "high"
    
    speed_map = {"low": random.randint(60, 90), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
    delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
    
    return {
        "level": level,
        "level_text": {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}[level],
        "avg_speed": speed_map[level],
        "delay_factor": delay_map[level],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "模擬數據"
    }


# ================= 2. 港口資料模擬（預留 API 接口） =================
# 港口固定資料（半真實）
PORT_DATA = {
    "KHH": {
        "name": "高雄港",
        "schedules": [
            {"ship_name": "YM Unity", "eta_hours": 3, "capacity": 200, "destination": "新加坡"},
            {"ship_name": "Ever Given", "eta_hours": 8, "capacity": 350, "destination": "洛杉磯"},
            {"ship_name": "MSC Oscar", "eta_hours": 15, "capacity": 500, "destination": "鹿特丹"},
        ]
    },
    "TXG": {
        "name": "台中港",
        "schedules": [
            {"ship_name": "Wan Hai 301", "eta_hours": 4, "capacity": 150, "destination": "香港"},
            {"ship_name": "Yang Ming 12", "eta_hours": 10, "capacity": 250, "destination": "東京"},
        ]
    },
    "KEL": {
        "name": "基隆港",
        "schedules": [
            {"ship_name": "CMA CGM", "eta_hours": 5, "capacity": 180, "destination": "上海"},
            {"ship_name": "HMM Cooperation", "eta_hours": 12, "capacity": 300, "destination": "釜山"},
        ]
    },
    "TPE": {
        "name": "台北港",
        "schedules": [
            {"ship_name": "TS Line", "eta_hours": 6, "capacity": 120, "destination": "廈門"},
        ]
    },
    "HUN": {
        "name": "花蓮港",
        "schedules": [
            {"ship_name": "Hualien Express", "eta_hours": 8, "capacity": 80, "destination": "石垣島"},
        ]
    }
}


def get_ship_schedule(port_code="KHH"):
    """
    獲取港口船期資訊
    
    真實資料來源（預留接口）：
    - iMarine 航港資料庫
    - MarineTraffic AIS API
    - 臺灣港務公司 API
    
    目前使用港口固定資料模擬
    """
    port_info = PORT_DATA.get(port_code, PORT_DATA["KHH"])
    
    # 取得最近的一班船
    if port_info["schedules"]:
        next_ship = port_info["schedules"][0]
        arrival_hours = next_ship["eta_hours"]
        ship_name = next_ship["ship_name"]
        available_capacity = next_ship["capacity"]
        destination = next_ship["destination"]
    else:
        arrival_hours = random.randint(1, 24)
        ship_name = "待定"
        available_capacity = random.randint(50, 200)
        destination = "未知"
    
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
    
    return {
        "port": port_code,
        "port_name": port_info["name"],
        "next_ship_name": ship_name,
        "next_ship_in_hours": arrival_hours,
        "next_ship_in_minutes": arrival_hours * 60,
        "status": status,
        "urgency": urgency,
        "available_capacity": available_capacity,
        "destination": destination,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "港口模擬資料（預留 API 串接）"
    }


# ================= 3. AI 多因子評分決策模型 =================
def calculate_sea_score(road_data, ship_data, cargo):
    """
    計算海運優勢分數（分數越高越推薦海運）
    """
    score = 0
    
    # 因子1：公路壅塞程度（最高 +3）
    if road_data["level"] == "high":
        score += 3
    elif road_data["level"] == "medium":
        score += 1.5
    
    # 因子2：船期急迫性（最高 +3）
    if ship_data["urgency"] == "high":
        score += 3
    elif ship_data["urgency"] == "medium":
        score += 2
    elif ship_data["urgency"] == "low":
        score += 0.5
    
    # 因子3：艙位充足性（最高 +2）
    if ship_data["available_capacity"] > 300:
        score += 2
    elif ship_data["available_capacity"] > 150:
        score += 1
    
    # 因子4：貨物適合海運（時間敏感度低）（最高 +2）
    sea_suitability = 1 - cargo.get("time_sensitivity", 0.3)
    score += sea_suitability * 2
    
    return score


def calculate_road_score(road_data, ship_data, cargo):
    """
    計算公路優勢分數（分數越高越推薦公路）
    """
    score = 0
    
    # 因子1：公路順暢（最高 +2）
    if road_data["level"] == "low":
        score += 2
    elif road_data["level"] == "medium":
        score += 0.5
    
    # 因子2：船期太久（最高 +2）
    if ship_data["urgency"] == "very_low":
        score += 2
    elif ship_data["urgency"] == "low":
        score += 1
    
    # 因子3：貨物時效性（最高 +5）
    score += cargo.get("time_sensitivity", 0.3) * 5
    
    # 因子4：短程距離（< 150km 公路優勢）（最高 +1）
    # 這個會在呼叫時傳入
    return score


def smart_dispatch_ai(containers, distance_km, road_data, ship_data, cargo):
    """
    AI 多因子評分決策引擎
    
    使用加權評分模型，而非單純的 if-else 規則
    """
    
    # 計算海運和公路的優勢分數
    sea_score = calculate_sea_score(road_data, ship_data, cargo)
    road_score = calculate_road_score(road_data, ship_data, cargo)
    
    # 短程距離加分（< 150km 公路優勢）
    if distance_km < 150:
        road_score += 1
    
    # 長程距離加分（> 400km 海運優勢）
    if distance_km > 400:
        sea_score += 1.5
    
    # 計算海運比例（分數越高，海運比例越高）
    total_score = sea_score + road_score
    if total_score > 0:
        sea_ratio = sea_score / total_score
    else:
        sea_ratio = 0.5
    
    # 限制比例範圍（20% - 80%）
    sea_ratio = max(0.2, min(0.8, sea_ratio))
    
    # 計算實際分配數量
    to_sea = int(containers * sea_ratio)
    to_road = containers - to_sea
    
    # 生成決策原因
    reasons = []
    if road_data["level"] == "high":
        reasons.append(f"公路嚴重壅塞（時速 {road_data['avg_speed']} km/h）")
    elif road_data["level"] == "medium":
        reasons.append(f"公路車多（時速 {road_data['avg_speed']} km/h）")
    
    if ship_data["urgency"] == "high":
        reasons.append(f"船舶 {ship_data['next_ship_in_hours']} 小時內到港")
    elif ship_data["urgency"] == "medium":
        reasons.append(f"船舶 {ship_data['next_ship_in_hours']} 小時內到港")
    
    if cargo.get("time_sensitivity", 0.3) > 0.7:
        reasons.append(f"貨物時效性高（敏感度 {cargo['time_sensitivity']*100:.0f}%）")
    
    if distance_km < 150:
        reasons.append(f"距離較短（{distance_km} km），公路有時間優勢")
    elif distance_km > 400:
        reasons.append(f"距離較長（{distance_km} km），海運有成本優勢")
    
    reason_text = "、".join(reasons) if reasons else "路況與船期正常"
    
    # 計算碳排效益
    road_emission_factor = 0.06
    sea_emission_factor = 0.02
    road_carbon = to_sea * distance_km * road_emission_factor
    sea_carbon = to_sea * distance_km * sea_emission_factor
    carbon_saved = road_carbon - sea_carbon
    carbon_saved_pct = (carbon_saved / road_carbon * 100) if road_carbon > 0 else 0
    
    return {
        "to_sea": to_sea,
        "to_road": to_road,
        "sea_ratio": round(sea_ratio * 100, 1),
        "road_ratio": round((1 - sea_ratio) * 100, 1),
        "sea_score": round(sea_score, 2),
        "road_score": round(road_score, 2),
        "reason": reason_text,
        "suggested_action": "transfer_to_sea" if to_sea > to_road else "keep_road",
        "carbon_benefit": {
            "saved": round(carbon_saved, 2),
            "saved_pct": round(carbon_saved_pct, 1),
            "road_carbon": round(road_carbon, 2),
            "sea_carbon": round(sea_carbon, 2)
        } if to_sea > 0 else None
    }


# 保持向後兼容的函數
def get_road_congestion(use_real_api=False):
    """
    獲取公路車況（可選擇使用真實 API 或模擬）
    """
    if use_real_api and TDX_APP_ID != "your_app_id":
        return get_road_congestion_real()
    else:
        return get_road_congestion_mock()


def smart_dispatch(containers, distance_km, road_data, ship_data, cargo):
    """
    智慧調度（使用 AI 評分模型）
    """
    return smart_dispatch_ai(containers, distance_km, road_data, ship_data, cargo)


# ================= 測試 =================
if __name__ == "__main__":
    print("=== AI 多因子評分決策模型測試 ===\n")
    
    # 測試不同情境
    test_scenarios = [
        {"name": "情境1：尖峰時段 + 船期佳", "hour": 8, "cargo_sensitivity": 0.3, "distance": 200},
        {"name": "情境2：離峰時段 + 高時效貨物", "hour": 14, "cargo_sensitivity": 0.9, "distance": 100},
        {"name": "情境3：長距離 + 大宗貨物", "hour": 10, "cargo_sensitivity": 0.2, "distance": 450},
    ]
    
    for scenario in test_scenarios:
        print(f"\n📌 {scenario['name']}")
        print(f"   距離: {scenario['distance']} km, 貨物敏感度: {scenario['cargo_sensitivity']}")
        
        # 模擬數據
        road = get_road_congestion_mock()
        ship = get_ship_schedule("KHH")
        cargo = {"time_sensitivity": scenario["cargo_sensitivity"]}
        
        print(f"   公路: {road['level_text']} (時速 {road['avg_speed']} km/h)")
        print(f"   船舶: {ship['status']} ({ship['next_ship_in_hours']} 小時後到港)")
        
        # AI 決策
        result = smart_dispatch_ai(100, scenario["distance"], road, ship, cargo)
        
        print(f"\n   🤖 AI 評分結果:")
        print(f"      海運分數: {result['sea_score']} | 公路分數: {result['road_score']}")
        print(f"      海運比例: {result['sea_ratio']}% | 公路比例: {result['road_ratio']}%")
        print(f"      分配結果: 海運 {result['to_sea']} FEU / 公路 {result['to_road']} FEU")
        print(f"      決策原因: {result['reason']}")
        if result['carbon_benefit']:
            print(f"      🌱 碳排效益: 減少 {result['carbon_benefit']['saved']} kg ({result['carbon_benefit']['saved_pct']}%)")