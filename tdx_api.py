"""
交通部 TDX API 串接模組
取得即時公路車速、壅塞資料、路網幾何
"""

import requests
from datetime import datetime
import random

class TDXAPI:
    def __init__(self, app_id=None, app_key=None):
        self.app_id = app_id or "YOUR_APP_ID"
        self.app_key = app_key or "YOUR_APP_KEY"
        self.token = None

    def get_token(self):
        url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.app_id,
            "client_secret": self.app_key
        }
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                return self.token
        except Exception as e:
            print(f"TDX API 錯誤: {e}")
        return None

    def get_highway_traffic(self, highway_id="1"):
        if not self.token and not self.get_token():
            return self._get_mock_data()

        url = f"https://tdx.transportdata.tw/api/basic/v3/Freeway/Expressway/Traffic/National{highway_id}"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                speeds = [item["Speed"] for item in data.get("Data", []) if "Speed" in item]
                avg_speed = sum(speeds) / len(speeds) if speeds else 80
                return self._calc_congestion(avg_speed, "TDX 即時 API")
        except Exception as e:
            print(f"取得高速公路資料錯誤: {e}")

        return self._get_mock_data()

    def get_live_network_traffic(self):
        """取得即時路網車流資料（含路段幾何）"""
        if not self.token and not self.get_token():
            return self._get_mock_network_traffic()

        # 即時車流 API
        url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/Freeway"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return self._parse_traffic_data(response.json())
        except Exception as e:
            print(f"取得即時路網資料錯誤: {e}")

        return self._get_mock_network_traffic()

    def _parse_traffic_data(self, data):
        """解析 TDX 即時路網資料"""
        roads = []
        
        for item in data.get("Roads", []):
            try:
                coords = []
                for p in item.get("Geometry", {}).get("Coordinates", []):
                    if "PositionLat" in p and "PositionLon" in p:
                        coords.append([p["PositionLat"], p["PositionLon"]])
                
                if len(coords) >= 2:
                    speed = item.get("Speed", 60)
                    
                    # 根據速度決定顏色
                    if speed >= 60:
                        color = "#27ae60"
                        level = "順暢"
                    elif speed >= 35:
                        color = "#f39c12"
                        level = "車多"
                    else:
                        color = "#e74c3c"
                        level = "壅塞"
                    
                    roads.append({
                        "coords": coords,
                        "speed": speed,
                        "color": color,
                        "level": level,
                        "name": item.get("Name", "未知路段")
                    })
            except Exception as e:
                print(f"解析路段錯誤: {e}")
                continue
        
        return roads

    def _get_mock_network_traffic(self):
        """模擬路網資料（API 無法使用時的備案）"""
        # 模擬國道一號北中南路段
        mock_roads = [
            {
                "coords": [[25.05, 121.52], [25.00, 121.45], [24.95, 121.38]],
                "speed": random.randint(15, 35),
                "name": "國道一號 汐止-台北"
            },
            {
                "coords": [[24.90, 121.30], [24.85, 121.20], [24.80, 121.10]],
                "speed": random.randint(40, 65),
                "name": "國道一號 台北-桃園"
            },
            {
                "coords": [[24.75, 121.00], [24.70, 120.90], [24.65, 120.80]],
                "speed": random.randint(55, 80),
                "name": "國道一號 桃園-新竹"
            },
            {
                "coords": [[24.60, 120.70], [24.55, 120.65], [24.50, 120.60]],
                "speed": random.randint(30, 55),
                "name": "國道一號 新竹-苗栗"
            },
            {
                "coords": [[24.45, 120.55], [24.35, 120.50], [24.25, 120.45]],
                "speed": random.randint(60, 85),
                "name": "國道一號 苗栗-台中"
            },
            {
                "coords": [[24.15, 120.40], [24.05, 120.35], [23.95, 120.30]],
                "speed": random.randint(20, 50),
                "name": "國道一號 台中-彰化"
            },
            {
                "coords": [[23.85, 120.25], [23.75, 120.20], [23.65, 120.15]],
                "speed": random.randint(45, 70),
                "name": "國道一號 彰化-雲林"
            },
            {
                "coords": [[23.55, 120.10], [23.45, 120.10], [23.35, 120.15]],
                "speed": random.randint(55, 80),
                "name": "國道一號 雲林-嘉義"
            },
            {
                "coords": [[23.25, 120.15], [23.10, 120.20], [22.95, 120.25]],
                "speed": random.randint(35, 60),
                "name": "國道一號 嘉義-台南"
            },
            {
                "coords": [[22.85, 120.25], [22.75, 120.28], [22.65, 120.30]],
                "speed": random.randint(25, 50),
                "name": "國道一號 台南-高雄"
            }
        ]
        
        for road in mock_roads:
            if road["speed"] >= 60:
                road["color"] = "#27ae60"
                road["level"] = "順暢"
            elif road["speed"] >= 35:
                road["color"] = "#f39c12"
                road["level"] = "車多"
            else:
                road["color"] = "#e74c3c"
                road["level"] = "壅塞"
        
        return mock_roads

    def _calc_congestion(self, avg_speed, source):
        if avg_speed >= 60:
            level, text = "low", "🟢 順暢"
        elif avg_speed >= 35:
            level, text = "medium", "🟡 車多"
        else:
            level, text = "high", "🔴 壅塞"

        delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
        return {
            "level": level,
            "level_text": text,
            "avg_speed": round(avg_speed, 1),
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source
        }

    def _get_mock_data(self):
        current_hour = datetime.now().hour
        
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            level = random.choice(["medium", "high"])
        else:
            level = random.choice(["low", "medium"])
        
        speed_map = {"low": random.randint(60, 90), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
        delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
        text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
        
        return {
            "level": level,
            "level_text": text_map[level],
            "avg_speed": speed_map[level],
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料 (備用)"
        }


# 單例模式，方便呼叫
_tdx_api = None

def get_tdx_api():
    global _tdx_api
    if _tdx_api is None:
        _tdx_api = TDXAPI()
    return _tdx_api

def get_road_congestion(use_api=True, app_id=None, app_key=None):
    if use_api and app_id and app_key:
        api = TDXAPI(app_id, app_key)
        return api.get_highway_traffic("1")
    else:
        current_hour = datetime.now().hour
        
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            level = random.choice(["medium", "high"])
        else:
            level = random.choice(["low", "medium"])
        
        speed_map = {"low": random.randint(60, 90), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
        delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
        text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
        
        return {
            "level": level,
            "level_text": text_map[level],
            "avg_speed": speed_map[level],
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料 (時段模擬)"
        }

def get_live_network_traffic():
    """取得即時路網車流資料"""
    api = get_tdx_api()
    return api.get_live_network_traffic()