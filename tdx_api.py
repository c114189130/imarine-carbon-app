"""
交通部 TDX API 串接模組
取得即時公路車速、壅塞資料
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
        """取得存取令牌"""
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
        """取得高速公路即時車速"""
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

    def _calc_congestion(self, avg_speed, source):
        """根據平均時速計算壅塞程度"""
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
        """模擬資料（API 無法使用時的備案）"""
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


def get_road_congestion(use_api=True, app_id=None, app_key=None):
    """
    取得公路壅塞資料
    
    參數:
        use_api: 是否使用真實 API（預設 True）
        app_id: TDX App ID（如需使用真實 API）
        app_key: TDX App Key（如需使用真實 API）
    """
    if use_api and app_id and app_key:
        api = TDXAPI(app_id, app_key)
        return api.get_highway_traffic("1")
    else:
        # 使用模擬資料
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