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

# 碳排放係數 (kg CO2e / km / FEU)（取每FEU平均值）
EMISSION_FACTORS = {
    "road": 0.098,   # 公路每FEU每公里碳排 (約40呎平均值)
    "sea": 0.024     # 海運每FEU每公里碳排 (約40呎平均值)
}

# 港口裝卸碳排 (kg CO2e / FEU)
PORT_HANDLING_EMISSION = 8.0

# 作業費費率 (NT$/km/FEU)
TRANSPORT_COST_RATES = {
    "road": 60,
    "sea": 24
}

# 碳權價格 (NT$/kg CO2e，參考歐盟ETS約80歐元/噸 ≈ 2800 NT$/噸)
CARBON_PRICE_PER_KG = 2.8

# 行駛速度 (km/h)
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 46

# TEU 轉 FEU 比例
TEU_TO_FEU_RATIO = 0.5

# 歷史記錄上限
MAX_HISTORY_RECORDS = 200

# 港口定義（新增「台北港」作為航線節點，但實際顯示用汐止調度場）
PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.300, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.270, "lon": 120.520, "code": "TXG"},
    "taipei": {"name": "汐止調度場(台北)", "lat": 25.066, "lon": 121.660, "code": "TPE"},
}

# 航線距離（直線+路網係數）及碳排放基準
ROUTES_INFO = {
    ("kaohsiung", "taichung"): {"road_km": 215, "sea_km": 175, "carbon_per_feu_road": 21.07, "carbon_per_feu_sea": 4.2},
    ("kaohsiung", "taipei"): {"road_km": 365, "sea_km": 310, "carbon_per_feu_road": 35.77, "carbon_per_feu_sea": 7.44},
    ("taichung", "taipei"): {"road_km": 170, "sea_km": 140, "carbon_per_feu_road": 16.66, "carbon_per_feu_sea": 3.36},
    ("taipei", "kaohsiung"): {"road_km": 365, "sea_km": 310, "carbon_per_feu_road": 35.77, "carbon_per_feu_sea": 7.44},
    ("taipei", "taichung"): {"road_km": 170, "sea_km": 140, "carbon_per_feu_road": 16.66, "carbon_per_feu_sea": 3.36},
}

# 檔案路徑
HISTORY_FILE = DATA_DIR / "history.json"
CERTIFICATE_FILE = DATA_DIR / "certificates.json"
SCHEDULE_FILE = DATA_DIR / "ship_schedule.json"

# 船班資料（立昌輪、立揚輪）
DEFAULT_SHIPS = {
    "KHH": {
        "port_name": "高雄港",
        "ships": [
            {"name": "立昌輪", "name_zh": "LI CHANG", "voyage": "LC-2401", "route": "TBS",
             "etd": "04/01 08:00", "eta": "04/02 06:00", "hours": 22, "capacity_teu": 1200, "capacity_feu": 600,
             "available_feu": 320, "destination": "台中港", "dest_code": "TXG", "schedule_day": "一、三、五",
             "next_sailings": [
                 {"etd": "04/01 08:00", "eta": "04/02 06:00", "available_feu": 320},
                 {"etd": "04/03 08:00", "eta": "04/04 06:00", "available_feu": 450},
                 {"etd": "04/05 08:00", "eta": "04/06 06:00", "available_feu": 280},
                 {"etd": "04/08 08:00", "eta": "04/09 06:00", "available_feu": 500}
             ]},
            {"name": "立揚輪", "name_zh": "LI YANG", "voyage": "LY-2401", "route": "TBS",
             "etd": "04/02 18:00", "eta": "04/03 16:00", "hours": 22, "capacity_teu": 1618, "capacity_feu": 809,
             "available_feu": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "二、四、六",
             "next_sailings": [
                 {"etd": "04/02 18:00", "eta": "04/03 16:00", "available_feu": 500},
                 {"etd": "04/04 18:00", "eta": "04/05 16:00", "available_feu": 600},
                 {"etd": "04/06 18:00", "eta": "04/07 16:00", "available_feu": 700},
                 {"etd": "04/09 18:00", "eta": "04/10 16:00", "available_feu": 800}
             ]}
        ]
    },
    "TXG": {
        "port_name": "台中港",
        "ships": [
            {"name": "立昌輪", "name_zh": "LI CHANG", "voyage": "LC-2402", "route": "TBN",
             "etd": "04/01 14:00", "eta": "04/02 02:00", "hours": 12, "capacity_teu": 1200, "capacity_feu": 600,
             "available_feu": 250, "destination": "汐止調度場(台北)", "dest_code": "TPE", "schedule_day": "一、三、五",
             "next_sailings": [
                 {"etd": "04/01 14:00", "eta": "04/02 02:00", "available_feu": 250},
                 {"etd": "04/03 14:00", "eta": "04/04 02:00", "available_feu": 350},
                 {"etd": "04/05 14:00", "eta": "04/06 02:00", "available_feu": 400}
             ]},
            {"name": "立揚輪", "name_zh": "LI YANG", "voyage": "LY-2402", "route": "TBN",
             "etd": "04/02 08:00", "eta": "04/02 20:00", "hours": 12, "capacity_teu": 1618, "capacity_feu": 809,
             "available_feu": 600, "destination": "汐止調度場(台北)", "dest_code": "TPE", "schedule_day": "二、四、六",
             "next_sailings": [
                 {"etd": "04/02 08:00", "eta": "04/02 20:00", "available_feu": 600},
                 {"etd": "04/04 08:00", "eta": "04/04 20:00", "available_feu": 700},
                 {"etd": "04/06 08:00", "eta": "04/06 20:00", "available_feu": 750}
             ]}
        ]
    },
    "TPE": {
        "port_name": "汐止調度場(台北)",
        "ships": [
            {"name": "立昌輪", "name_zh": "LI CHANG", "voyage": "LC-2403", "route": "TBS",
             "etd": "04/02 06:00", "eta": "04/03 04:00", "hours": 22, "capacity_teu": 1200, "capacity_feu": 600,
             "available_feu": 300, "destination": "高雄港", "dest_code": "KHH", "schedule_day": "二、四、六",
             "next_sailings": [
                 {"etd": "04/02 06:00", "eta": "04/03 04:00", "available_feu": 300},
                 {"etd": "04/04 06:00", "eta": "04/05 04:00", "available_feu": 400}
             ]},
            {"name": "立揚輪", "name_zh": "LI YANG", "voyage": "LY-2403", "route": "TBS",
             "etd": "04/03 12:00", "eta": "04/04 10:00", "hours": 22, "capacity_teu": 1618, "capacity_feu": 809,
             "available_feu": 650, "destination": "高雄港", "dest_code": "KHH", "schedule_day": "三、五",
             "next_sailings": [
                 {"etd": "04/03 12:00", "eta": "04/04 10:00", "available_feu": 650},
                 {"etd": "04/05 12:00", "eta": "04/06 10:00", "available_feu": 750}
             ]},
            {"name": "立昌輪", "name_zh": "LI CHANG", "voyage": "LC-2404", "route": "TBN",
             "etd": "04/01 20:00", "eta": "04/02 08:00", "hours": 12, "capacity_teu": 1200, "capacity_feu": 600,
             "available_feu": 200, "destination": "台中港", "dest_code": "TXG", "schedule_day": "一、三、五",
             "next_sailings": [
                 {"etd": "04/01 20:00", "eta": "04/02 08:00", "available_feu": 200},
                 {"etd": "04/03 20:00", "eta": "04/04 08:00", "available_feu": 350}
             ]}
        ]
    }
}