"""
交通部 TDX API 串接模組 - 優化版
只回傳必要資料，減少傳輸量
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
        data = {"grant_type": "client_credentials", "client_id": self.app_id, "client_secret": self.app_key}
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                return self.token
        except Exception as e:
            print(f"TDX API 錯誤: {e}")
        return None

    def get_live_traffic_speed(self):
        """只回傳路段 ID 和速度，減少傳輸量"""
        if not self.token and not self.get_token():
            return self._get_mock_speed_data()
        
        url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/Freeway"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return self._parse_speed_only(response.json())
        except Exception as e:
            print(f"取得即時路網資料錯誤: {e}")
        
        return self._get_mock_speed_data()
    
    def _parse_speed_only(self, data):
        """只解析路段 ID 和速度"""
        roads = []
        for item in data.get("Roads", []):
            try:
                road_id = item.get("Id", f"NH1-{len(roads)}")
                speed = item.get("Speed", 60)
                roads.append({"id": road_id, "speed": speed})
            except:
                continue
        return roads
    
    def _get_mock_speed_data(self):
        """模擬速度資料（輕量級）"""
        import random
        road_ids = ["NH1-S-0", "NH1-S-1", "NH1-S-2", "NH1-S-3", "NH1-S-4"]
        return [{"id": rid, "speed": random.randint(20, 90)} for rid in road_ids]

_tdx_api = None

def get_live_traffic_speed():
    global _tdx_api
    if _tdx_api is None:
        _tdx_api = TDXAPI()
    return _tdx_api.get_live_traffic_speed()