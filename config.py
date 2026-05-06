import os
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_TITLE = "iMarine 智慧藍色公路運輸決策平台"
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

TDX_CLIENT_ID = os.environ.get("TDX_CLIENT_ID", "")
TDX_CLIENT_SECRET = os.environ.get("TDX_CLIENT_SECRET", "")

# 碳排放係數
EMISSION_FACTORS = {"road": 0.098, "sea": 0.024}
PORT_HANDLING_EMISSION = 8.0

# 成本費率
TRANSPORT_COST_RATES = {"road": 60, "sea": 24}
PORT_HANDLING_FEE = 1200
ROAD_TOLL_RATE = 2.5

# 碳權價格 (NT$/kg CO2e)
CARBON_PRICE_PER_KG = 2.8

# 速度
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 30

# VSL 人命價值
VSL = 50_000_000
ACCIDENT_RATE = {"road": 0.015, "sea": 0.0005}

# 貨物類型
CARGO_TYPES = {
    "normal": {"name": "一般貨物", "risk_factor": 1.0, "time_sensitivity": 1.0},
    "cold_chain": {"name": "冷鏈貨物", "risk_factor": 1.5, "time_sensitivity": 2.0},
    "dangerous": {"name": "危險品", "risk_factor": 3.0, "time_sensitivity": 1.2},
}

TEU_TO_FEU = 0.5
MAX_HISTORY_RECORDS = 200

# SDG 指標
SDG_INDICATORS = {
    "sdg9": "產業創新與基礎設施",
    "sdg11": "永續城市與社區",
    "sdg13": "氣候行動",
    "sdg14": "海洋生態",
}

PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.300, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.270, "lon": 120.520, "code": "TXG"},
    "taipei": {"name": "汐止調度場(台北)", "lat": 25.066, "lon": 121.660, "code": "TPE"},
}

ROUTES = {
    ("kaohsiung", "taichung"): {"road_km": 215, "sea_km": 175},
    ("kaohsiung", "taipei"):   {"road_km": 365, "sea_km": 310},
    ("taichung", "taipei"):    {"road_km": 170, "sea_km": 140},
}

SHIP_SCHEDULE_BASE = {
    "KHH": [
        {"name": "立昌輪", "en": "LI CHANG", "weekday": 1, "etd_hour": 8, "hours": 22, "capacity_feu": 809, "dest": "TXG"},
        {"name": "立昌輪", "en": "LI CHANG", "weekday": 4, "etd_hour": 8, "hours": 22, "capacity_feu": 809, "dest": "TXG"},
        {"name": "立揚輪", "en": "LI YANG", "weekday": 2, "etd_hour": 18, "hours": 22, "capacity_feu": 809, "dest": "TXG"},
        {"name": "立揚輪", "en": "LI YANG", "weekday": 5, "etd_hour": 18, "hours": 22, "capacity_feu": 809, "dest": "TXG"},
    ],
    "TXG": [
        {"name": "立昌輪", "en": "LI CHANG", "weekday": 1, "etd_hour": 14, "hours": 12, "capacity_feu": 809, "dest": "TPE"},
        {"name": "立昌輪", "en": "LI CHANG", "weekday": 4, "etd_hour": 14, "hours": 12, "capacity_feu": 809, "dest": "TPE"},
        {"name": "立揚輪", "en": "LI YANG", "weekday": 2, "etd_hour": 8, "hours": 12, "capacity_feu": 809, "dest": "TPE"},
        {"name": "立揚輪", "en": "LI YANG", "weekday": 5, "etd_hour": 8, "hours": 12, "capacity_feu": 809, "dest": "TPE"},
    ],
    "TPE": [
        {"name": "立昌輪", "en": "LI CHANG", "weekday": 1, "etd_hour": 6, "hours": 22, "capacity_feu": 809, "dest": "KHH"},
        {"name": "立揚輪", "en": "LI YANG", "weekday": 2, "etd_hour": 12, "hours": 22, "capacity_feu": 809, "dest": "KHH"},
    ],
}

HISTORY_FILE = DATA_DIR / "history.json"
CERTIFICATE_FILE = DATA_DIR / "certificates.json"


def generate_year_schedule(start_code, end_code, year=2026):
    ships = SHIP_SCHEDULE_BASE.get(start_code, [])
    schedule = []
    current = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    while current <= end:
        wd = current.weekday()
        for ship in ships:
            if ship["dest"] == end_code and ship["weekday"] == wd:
                etd_dt = current.replace(hour=ship["etd_hour"], minute=0)
                eta_dt = etd_dt + timedelta(hours=ship["hours"])
                schedule.append({
                    "ship": f"{ship['name']}({ship['en']})",
                    "etd": etd_dt.strftime("%Y/%m/%d %H:%M"),
                    "eta": eta_dt.strftime("%Y/%m/%d %H:%M"),
                    "hours": ship["hours"],
                    "capacity_feu": ship["capacity_feu"],
                })
        current += timedelta(days=1)
    return schedule