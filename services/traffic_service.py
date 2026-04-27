"""
交通部 TDX API 即時路況服務
"""

import os
import requests
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# 國道路段定義
FREEWAY_SEGMENTS = [
    {"id": "NH1-N-0", "name": "國道一號 基隆-台北", "direction": "北", "highway": "國道一號"},
    {"id": "NH1-S-1", "name": "國道一號 台北-桃園", "direction": "南", "highway": "國道一號"},
    {"id": "NH1-S-2", "name": "國道一號 桃園-新竹", "direction": "南", "highway": "國道一號"},
    {"id": "NH1-S-3", "name": "國道一號 新竹-台中", "direction": "南", "highway": "國道一號"},
    {"id": "NH1-S-4", "name": "國道一號 台中-高雄", "direction": "南", "highway": "國道一號"},
    {"id": "NH3-N-0", "name": "國道三號 基隆-台北", "direction": "北", "highway": "國道三號"},
    {"id": "NH3-S-1", "name": "國道三號 台北-桃園", "direction": "南", "highway": "國道三號"},
    {"id": "NH3-S-2", "name": "國道三號 桃園-新竹", "direction": "南", "highway": "國道三號"},
    {"id": "NH3-S-3", "name": "國道三號 新竹-台中", "direction": "南", "highway": "國道三號"},
    {"id": "NH3-S-4", "name": "國道三號 台中-彰化", "direction": "南", "highway": "國道三號"},
    {"id": "NH3-S-5", "name": "國道三號 彰化-高雄", "direction": "南", "highway": "國道三號"},
    {"id": "NH5-S-0", "name": "國道五號 南港-宜蘭", "direction": "南", "highway": "國道五號"},
]


class TrafficService:
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None):
        self.app_id = app_id or os.environ.get("TDX_APP_ID", "")
        self.app_key = app_key or os.environ.get("TDX_APP_KEY", "")
        self._token = None
        self._token_expiry = None
        self._use_mock = not (self.app_id and self.app_key)

    def _get_token(self) -> Optional[str]:
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.app_id,
            "client_secret": self.app_key,
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self._token = result.get("access_token")
                expires_in = result.get("expires_in", 3600)
                self._token_expiry = datetime.now()
                print(f"✅ TDX Token 取得成功")
                return self._token
            else:
                print(f"❌ TDX Token 取得失敗: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ TDX API 連線錯誤: {e}")

        self._use_mock = True
        return None

    def _fetch_real_traffic(self) -> List[Dict[str, Any]]:
        token = self._get_token()
        if not token:
            print("⚠️ 無法取得 TDX Token，使用模擬資料")
            return self._get_mock_traffic()

        url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/Freeway"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ TDX API 成功取得 {len(data.get('Roads', []))} 筆路段資料")
                return self._parse_traffic_data(data)
            else:
                print(f"❌ TDX API 錯誤: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ TDX API 連線錯誤: {e}")

        return self._get_mock_traffic()

    def _parse_traffic_data(self, data: dict) -> List[Dict[str, Any]]:
        results = []
        roads = data.get("Roads", [])

        for item in roads:
            road_id = item.get("Id", "")
            speed = item.get("Speed", 0)
            travel_time = item.get("TravelTime", 0)
            name = item.get("Name", road_id)

            matched = False
            for segment in FREEWAY_SEGMENTS:
                if segment["name"] in name or name in segment["name"]:
                    results.append({
                        "id": segment["id"],
                        "name": segment["name"],
                        "highway": segment["highway"],
                        "speed": speed,
                        "travel_time_minutes": round(travel_time / 60, 1) if travel_time else None,
                        "level": self._speed_to_level(speed),
                        "color": self._speed_to_color(speed),
                        "source": "TDX 即時 API",
                        "timestamp": datetime.now().isoformat(),
                    })
                    matched = True
                    break

            if not matched and speed > 0:
                results.append({
                    "id": road_id,
                    "name": name,
                    "highway": "國道",
                    "speed": speed,
                    "travel_time_minutes": round(travel_time / 60, 1) if travel_time else None,
                    "level": self._speed_to_level(speed),
                    "color": self._speed_to_color(speed),
                    "source": "TDX 即時 API",
                    "timestamp": datetime.now().isoformat(),
                })

        existing_ids = {r["id"] for r in results}
        for segment in FREEWAY_SEGMENTS:
            if segment["id"] not in existing_ids:
                results.append(self._mock_segment(segment))

        return results

    def _speed_to_level(self, speed: float) -> str:
        if speed >= 60:
            return "low"
        elif speed >= 35:
            return "medium"
        else:
            return "high"

    def _speed_to_color(self, speed: float) -> str:
        if speed >= 60:
            return "#27ae60"
        elif speed >= 35:
            return "#f39c12"
        else:
            return "#e74c3c"

    def _mock_segment(self, segment: dict) -> dict:
        current_hour = datetime.now().hour
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            speed = random.randint(25, 65)
        else:
            speed = random.randint(50, 100)

        return {
            "id": segment["id"],
            "name": segment["name"],
            "highway": segment["highway"],
            "speed": speed,
            "travel_time_minutes": random.randint(15, 90),
            "level": self._speed_to_level(speed),
            "color": self._speed_to_color(speed),
            "source": "模擬資料 (路段補償)",
            "timestamp": datetime.now().isoformat(),
        }

    def _get_mock_traffic(self) -> List[Dict[str, Any]]:
        results = []
        for segment in FREEWAY_SEGMENTS:
            current_hour = datetime.now().hour
            if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
                speed = random.randint(25, 65)
            else:
                speed = random.randint(50, 100)

            results.append({
                "id": segment["id"],
                "name": segment["name"],
                "highway": segment["highway"],
                "speed": speed,
                "travel_time_minutes": random.randint(15, 90),
                "level": self._speed_to_level(speed),
                "color": self._speed_to_color(speed),
                "source": "模擬資料 (時段模擬)",
                "timestamp": datetime.now().isoformat(),
            })
        return results

    def get_live_traffic_speed(self) -> List[Dict[str, Any]]:
        if self._use_mock:
            print("⚠️ 使用模擬路況模式")
            traffic_data = self._get_mock_traffic()
        else:
            traffic_data = self._fetch_real_traffic()

        return [{"id": item["id"], "speed": item["speed"]} for item in traffic_data]

    def get_full_traffic(self) -> List[Dict[str, Any]]:
        if self._use_mock:
            return self._get_mock_traffic()
        return self._fetch_real_traffic()

    def get_summary(self) -> Dict[str, Any]:
        traffic = self.get_full_traffic()
        speeds = [t["speed"] for t in traffic]
        avg_speed = sum(speeds) / len(speeds) if speeds else 60
        congested = len([t for t in traffic if t["level"] == "high"])
        smooth = len([t for t in traffic if t["level"] == "low"])

        return {
            "avg_speed": round(avg_speed, 1),
            "congested_count": congested,
            "smooth_count": smooth,
            "total_segments": len(traffic),
            "timestamp": datetime.now().isoformat(),
        }

    def summarize_traffic(self) -> Dict[str, Any]:
        summary = self.get_summary()
        if summary["avg_speed"] >= 60:
            level = "low"
        elif summary["avg_speed"] >= 35:
            level = "medium"
        else:
            level = "high"

        return {
            "level": level,
            "avg_speed": summary["avg_speed"],
        }