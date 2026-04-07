"""
數據獲取模組 - 支援真實 API 串接
目前使用 Mock 數據，換成真實 API 只需修改 URL
"""

import requests
import json
from datetime import datetime

# ================= 1. iMarine 航運 API =================
def get_sea_route(start_port, end_port):
    """
    獲取海運路線數據
    真 API: https://api.imarine.tw/routes
    """
    try:
        # 🔥 真 API 替換範例（取消註解即可使用）
        # url = "https://api.imarine.tw/v1/routes"
        # params = {"start": start_port, "end": end_port}
        # headers = {"Authorization": "Bearer YOUR_API_KEY"}
        # response = requests.get(url, params=params, headers=headers, timeout=10)
        # return response.json()
        
        # 目前使用 Mock 數據
        mock_routes = {
            ("kaohsiung", "taichung"): {"distance": 190, "time": 8, "congestion": 0.2, "fuel_cost": 8500},
            ("kaohsiung", "keelung"): {"distance": 380, "time": 16, "congestion": 0.3, "fuel_cost": 17000},
            ("kaohsiung", "taipei"): {"distance": 360, "time": 15, "congestion": 0.25, "fuel_cost": 16000},
            ("kaohsiung", "hualien"): {"distance": 280, "time": 12, "congestion": 0.15, "fuel_cost": 12500},
            ("taichung", "kaohsiung"): {"distance": 190, "time": 8, "congestion": 0.2, "fuel_cost": 8500},
            ("taichung", "keelung"): {"distance": 200, "time": 9, "congestion": 0.25, "fuel_cost": 9000},
            ("keelung", "kaohsiung"): {"distance": 380, "time": 16, "congestion": 0.3, "fuel_cost": 17000},
        }
        
        key = (start_port, end_port)
        if key in mock_routes:
            return mock_routes[key]
        else:
            return {"distance": 250, "time": 11, "congestion": 0.2, "fuel_cost": 11000}
            
    except Exception as e:
        print(f"海運 API 錯誤: {e}")
        return {"distance": 250, "time": 11, "congestion": 0.2, "fuel_cost": 11000}

# ================= 2. 公路局 API =================
def get_road_data(start_port, end_port):
    """
    獲取公路運輸數據
    真 API: https://api.thb.gov.tw/route
    """
    try:
        # 🔥 真 API 替換範例
        # url = "https://api.thb.gov.tw/v1/freight/route"
        # params = {"origin": start_port, "destination": end_port}
        # response = requests.get(url, params=params, timeout=10)
        # return response.json()
        
        # Mock 數據（公路通常比海運距離稍長）
        base_distance = 250
        return {
            "distance": base_distance,
            "time": base_distance / 60,
            "congestion": 0.6,
            "toll_cost": base_distance * 1.2,
            "fuel_cost": base_distance * 3.5
        }
        
    except Exception as e:
        print(f"公路 API 錯誤: {e}")
        return {"distance": 250, "time": 4.2, "congestion": 0.6, "toll_cost": 300, "fuel_cost": 875}

# ================= 3. 燃油價格 API =================
def get_fuel_prices():
    """
    獲取即時燃油價格
    真 API: EIA / 台灣中油
    """
    try:
        # 🔥 真 API: 美國能源資訊署 (EIA)
        # url = "https://api.eia.gov/v2/petroleum/pri/spt/data"
        # params = {"api_key": "YOUR_EIA_KEY"}
        # response = requests.get(url, params=params)
        # return response.json()
        
        return {
            "bunker_fuel": 620,
            "diesel": 32.5,
            "gasoline": 30.8,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "台灣中油參考價格"
        }
        
    except Exception as e:
        print(f"燃油價格 API 錯誤: {e}")
        return {"bunker_fuel": 620, "diesel": 32.5, "gasoline": 30.8}

# ================= 4. 港口吞吐量 API =================
def get_port_capacity(port_code):
    """
    獲取港口吞吐量數據
    真 API: TDX 交通數據平台
    """
    try:
        capacities = {
            "KHH": 10400000,
            "TXG": 1800000,
            "KEL": 1600000,
            "TPE": 1800000,
            "HUN": 800000
        }
        return {
            "port_code": port_code,
            "annual_teu": capacities.get(port_code, 1000000),
            "growth_rate": 0.03,
            "last_update": "2023"
        }
        
    except Exception as e:
        print(f"港口 API 錯誤: {e}")
        return {"annual_teu": 1000000, "growth_rate": 0.03}

# ================= 5. 天氣與海象 API =================
def get_weather_condition(port_code):
    """
    獲取港口天氣狀況
    真 API: 中央氣象局
    """
    try:
        return {
            "wind_speed": 12,
            "wave_height": 1.5,
            "visibility": "良好",
            "suitable_for_sailing": True
        }
    except Exception as e:
        return {"wind_speed": 10, "wave_height": 1.2, "suitable_for_sailing": True}

if __name__ == "__main__":
    print("=== 測試 API 模組 ===")
    print("海運路線:", get_sea_route("kaohsiung", "taichung"))
    print("公路數據:", get_road_data("kaohsiung", "taichung"))
    print("燃油價格:", get_fuel_prices())
    print("港口容量:", get_port_capacity("KHH"))