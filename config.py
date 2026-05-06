import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_TITLE = "iMarine 智慧藍色公路運輸決策系統"
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# TDX API 公路金鑰
TDX_CLIENT_ID = os.environ.get("TDX_CLIENT_ID", "")
TDX_CLIENT_SECRET = os.environ.get("TDX_CLIENT_SECRET", "")

# 碳排放係數 (kg CO2e / km / FEU)
EMISSION_FACTORS = {"road": 0.098, "sea": 0.024}

# 港口裝卸碳排 (kg CO2e / FEU)
PORT_HANDLING_EMISSION = 8.0

# 運輸成本費率 (NT$/km/FEU)
TRANSPORT_COST_RATES = {"road": 60, "sea": 24}
PORT_HANDLING_FEE = 1200  # 港口作業費 (NT$/FEU)
ROAD_TOLL_RATE = 2.5      # 公路過路費 (NT$/km/FEU)

# 碳權價格 (NT$/kg CO2e)
CARBON_PRICE_PER_KG = 2.8

# 速度 (km/h)
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 46

CONGESTION_FACTOR = {"low": 1.0, "medium": 1.2, "high": 1.5}

TEU_TO_FEU = 0.5
MAX_HISTORY_RECORDS = 200

# 港口定義
PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.300, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.270, "lon": 120.520, "code": "TXG"},
    "taipei": {"name": "汐止調度場(台北)", "lat": 25.066, "lon": 121.660, "code": "TPE"},
}

# 航線距離 (km) - 保留主要三條
ROUTES = {
    ("kaohsiung", "taichung"): {"road_km": 215, "sea_km": 175},
    ("kaohsiung", "taipei"):   {"road_km": 365, "sea_km": 310},
    ("taichung", "taipei"):    {"road_km": 170, "sea_km": 140},
}

# 船班資料 (立昌輪: 1618 TEU = 809 FEU)
# 立昌輪：週二、週五
# 立揚輪：週三、週六
SHIP_SCHEDULE = {
    "KHH": [
        {"name": "立昌輪", "en": "LI CHANG", "weekdays": [1,4], "etd_hour": 8,
         "hours": 22, "capacity_feu": 809, "dest": "TXG"},
        {"name": "立揚輪", "en": "LI YANG", "weekdays": [2,5], "etd_hour": 18,
         "hours": 22, "capacity_feu": 809, "dest": "TXG"},
    ],
    "TXG": [
        {"name": "立昌輪", "en": "LI CHANG", "weekdays": [1,4], "etd_hour": 14,
         "hours": 12, "capacity_feu": 809, "dest": "TPE"},
        {"name": "立揚輪", "en": "LI YANG", "weekdays": [2,5], "etd_hour": 8,
         "hours": 12, "capacity_feu": 809, "dest": "TPE"},
    ],
    "TPE": [
        {"name": "立昌輪", "en": "LI CHANG", "weekdays": [1,4], "etd_hour": 6,
         "hours": 22, "capacity_feu": 809, "dest": "KHH"},
        {"name": "立揚輪", "en": "LI YANG", "weekdays": [2,4], "etd_hour": 12,
         "hours": 22, "capacity_feu": 809, "dest": "KHH"},
    ],
}

# 檔案路徑
HISTORY_FILE = DATA_DIR / "history.json"
CERTIFICATE_FILE = DATA_DIR / "certificates.json"