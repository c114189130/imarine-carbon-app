"""
交通部 TDX API 串接模組
取得即時公路車速、壅塞資料
API 文件：https://tdx.transportdata.tw/api-service/swagger
"""

import requests
import json
from datetime import datetime

class TDXAPI:
    def __init__(self, app_id=None, app_key=None):
        """
        初始化 TDX API
        
        申請方式：
        1. 前往 https://tdx.transportdata.tw
        2. 註冊帳號
        3. 取得 App ID 和 App Key
        """
        self.app_id = app_id or "YOUR_APP_ID"
        self.app_key = app_key or "YOUR_APP_KEY"
        self.token = None
        self.token_expiry = None
    
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
                result = response.json()
                self.token = result.get("access_token")
                return self.token
            else:
                print(f"Token 取得失敗: {response.status_code}")
                return None
        except Exception as e:
            print(f"TDX API 錯誤: {e}")
            return None
    
    def get_live_traffic(self, city="Taipei"):
        """
        取得即時車速資料
        
        參數:
            city: 城市名稱 (Taipei, NewTaipei, Taichung, Kaohsiung 等)
        """
        if not self.token:
            self.get_token()
        
        if not self.token:
            return self._get_mock_traffic_data()
        
        # API 網址（即時車速）
        url = f"https://tdx.transportdata.tw/api/basic/v3/Road/LiveTraffic/City/{city}"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._parse_traffic_data(data)
            else:
                return self._get_mock_traffic_data()
        except Exception as e:
            print(f"取得即時路況錯誤: {e}")
            return self._get_mock_traffic_data()
    
    def get_highway_traffic(self, highway_id="1"):
        """
        取得高速公路即時車速（國道）
        
        參數:
            highway_id: 國道編號 (1, 3, 5 等)
        """
        if not self.token:
            self.get_token()
        
        if not self.token:
            return self._get_mock_highway_data()
        
        url = f"https://tdx.transportdata.tw/api/basic/v3/Freeway/Expressway/Traffic/National{highway_id}"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._parse_highway_data(data)
            else:
                return self._get_mock_highway_data()
        except Exception as e:
            print(f"取得高速公路資料錯誤: {e}")
            return self._get_mock_highway_data()
    
    def _parse_traffic_data(self, data):
        """解析即時車速資料"""
        if not data or not data.get("Data"):
            return self._get_mock_traffic_data()
        
        speeds = []
        for item in data["Data"]:
            if "TravelSpeed" in item:
                speeds.append(item["TravelSpeed"])
        
        avg_speed = sum(speeds) / len(speeds) if speeds else 50
        
        return self._calculate_congestion_from_speed(avg_speed)
    
    def _parse_highway_data(self, data):
        """解析高速公路資料"""
        if not data or not data.get("Data"):
            return self._get_mock_highway_data()
        
        speeds = []
        for item in data["Data"]:
            if "Speed" in item:
                speeds.append(item["Speed"])
        
        avg_speed = sum(speeds) / len(speeds) if speeds else 80
        
        return self._calculate_congestion_from_speed(avg_speed)
    
    def _calculate_congestion_from_speed(self, avg_speed):
        """根據平均時速計算壅塞程度"""
        if avg_speed >= 60:
            level = "low"
            level_text = "🟢 順暢"
        elif avg_speed >= 35:
            level = "medium"
            level_text = "🟡 車多"
        else:
            level = "high"
            level_text = "🔴 壅塞"
        
        delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
        
        return {
            "level": level,
            "level_text": level_text,
            "avg_speed": round(avg_speed, 1),
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "TDX API (即時資料)"
        }
    
    def _get_mock_traffic_data(self):
        """模擬資料（API 無法使用時的備案）"""
        import random
        current_hour = datetime.now().hour
        
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            level = random.choice(["medium", "high"])
        else:
            level = random.choice(["low", "medium"])
        
        speed_map = {"low": random.randint(60, 85), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
        delay_map = {"low": 1.0, "medium": 1.6, "high": 2.5}
        text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
        
        return {
            "level": level,
            "level_text": text_map[level],
            "avg_speed": speed_map[level],
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料 (API 未設定)"
        }
    
    def _get_mock_highway_data(self):
        """模擬高速公路資料"""
        import random
        level = random.choice(["low", "medium", "high"])
        speed_map = {"low": random.randint(80, 110), "medium": random.randint(50, 79), "high": random.randint(20, 49)}
        delay_map = {"low": 1.0, "medium": 1.5, "high": 2.2}
        text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
        
        return {
            "level": level,
            "level_text": text_map[level],
            "avg_speed": speed_map[level],
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料 (高速公路)"
        }


# 簡化版函數（向後相容）
def get_road_congestion(use_api=True, app_id=None, app_key=None):
    """
    取得公路壅塞資料
    
    參數:
        use_api: 是否使用真實 API（預設 True）
        app_id: TDX App ID
        app_key: TDX App Key
    """
    if use_api and app_id and app_key:
        api = TDXAPI(app_id, app_key)
        return api.get_highway_traffic("1")
    else:
        # 使用模擬資料（含時間因素）
        import random
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
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
        text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
        
        return {
            "level": level,
            "level_text": text_map[level],
            "avg_speed": speed_map[level],
            "delay_factor": delay_map[level],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "模擬資料 (時段模擬)"
        }


if __name__ == "__main__":
    print("=== TDX API 測試 ===\n")
    
    # 測試模擬資料
    print("1. 模擬資料模式:")
    data = get_road_congestion(use_api=False)
    print(f"   壅塞程度: {data['level_text']}")
    print(f"   平均時速: {data['avg_speed']} km/h")
    print(f"   延遲倍數: {data['delay_factor']}x")
    
    # 如果設定了 API 憑證，測試真實 API
    # app_id = "你的App ID"
    # app_key = "你的App Key"
    # if app_id != "YOUR_APP_ID":
    #     print("\n2. 真實 API 模式:")
    #     real_data = get_road_congestion(use_api=True, app_id=app_id, app_key=app_key)
    #     print(f"   壅塞程度: {real_data['level_text']}")
    #     print(f"   平均時速: {real_data['avg_speed']} km/h")