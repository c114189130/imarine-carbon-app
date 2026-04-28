import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(exist_ok=True)

APP_TITLE = "iMarine 智慧海運碳排管理系統"
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# TDX API 憑證（從環境變數讀取）
TDX_CLIENT_ID = os.environ.get("TDX_CLIENT_ID", "")
TDX_CLIENT_SECRET = os.environ.get("TDX_CLIENT_SECRET", "")

# 碳排放係數 (kg CO2e / km / FEU)
EMISSION_FACTORS = {"road": 0.06, "sea": 0.02}

# 作業費費率 (NT$/km/FEU)
TRANSPORT_COST_RATES = {"road": 60, "sea": 24}

# 行駛速度 (km/h)
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 46

# 港口裝卸碳排 (kg CO2e / FEU)
PORT_HANDLING_EMISSION_PER_CONTAINER = 8.0

# 歷史記錄上限
MAX_HISTORY_RECORDS = 200

# 港口定義
PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.300, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.270, "lon": 120.520, "code": "TXG"},
    "taipei": {"name": "汐止調度場", "lat": 25.066, "lon": 121.660, "code": "TPE"},
}

# 檔案路徑
HISTORY_FILE = DATA_DIR / "history.json"
CERTIFICATE_FILE = DATA_DIR / "certificates.json"
SCHEDULE_FILE = DATA_DIR / "evergreen_schedule.json"

# 預設船班資料
DEFAULT_SCHEDULE = {
    "KHH": {
        "port_name": "高雄港",
        "ships": [
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5021B", "route": "TBS", "etd": "03/01 08:00", "eta": "03/02 09:30", "hours": 25.5, "available": 320, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "FRI"},
            {"name": "UNI-PROSPER", "name_zh": "立福輸", "voyage": "E5022B", "route": "TBS", "etd": "03/04 17:00", "eta": "03/05 13:30", "hours": 20.5, "available": 280, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "TUE"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5023B", "route": "TBS", "etd": "03/05 10:00", "eta": "03/06 04:30", "hours": 18.5, "available": 350, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "WED"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5024B", "route": "TBS", "etd": "03/09 22:00", "eta": "03/10 15:00", "hours": 17.0, "available": 400, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "SUN"},
            {"name": "UNI-PROSPER", "name_zh": "立福輸", "voyage": "E5025B", "route": "TBS", "etd": "03/11 20:00", "eta": "03/12 22:00", "hours": 26.0, "available": 300, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "TUE"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5026B", "route": "TBS", "etd": "03/12 08:00", "eta": "03/13 10:00", "hours": 26.0, "available": 250, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "WED"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5027B", "route": "TBS", "etd": "03/15 14:00", "eta": "03/16 17:30", "hours": 27.5, "available": 380, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "SAT"},
            {"name": "UNI-PROSPER", "name_zh": "立福輸", "voyage": "E5028B", "route": "TBS", "etd": "03/19 01:00", "eta": "03/20 00:30", "hours": 23.5, "available": 450, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "WED"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5029B", "route": "TBS", "etd": "03/19 11:00", "eta": "03/20 22:30", "hours": 35.5, "available": 200, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "WED"},
            {"name": "UNI-PROMOTE", "name_zh": "立福輸", "voyage": "E5030B", "route": "TBS", "etd": "03/22 19:00", "eta": "03/23 09:00", "hours": 14.0, "available": 150, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "SAT"},
            {"name": "UNI-PROSPER", "name_zh": "立福輸", "voyage": "E5031B", "route": "TBS", "etd": "03/25 23:00", "eta": "03/26 13:00", "hours": 14.0, "available": 500, "capacity": 500, "destination": "台中港", "dest_code": "TXG", "schedule_day": "TUE"}
        ]
    },
    "TXG": {
        "port_name": "台中港",
        "ships": [
            {"name": "EVERGREEN V-201", "name_zh": "長榮虛擬", "voyage": "V201A", "route": "TBN", "etd": "03/02 08:00", "eta": "03/02 18:00", "hours": 10.0, "available": 200, "capacity": 300, "destination": "汐止調度場", "dest_code": "TPE", "schedule_day": "MON"},
            {"name": "EVERGREEN V-202", "name_zh": "長榮虛擬", "voyage": "V202A", "route": "TBN", "etd": "03/04 08:00", "eta": "03/04 18:00", "hours": 10.0, "available": 250, "capacity": 300, "destination": "汐止調度場", "dest_code": "TPE", "schedule_day": "WED"},
            {"name": "EVERGREEN V-203", "name_zh": "長榮虛擬", "voyage": "V203A", "route": "TBN", "etd": "03/06 08:00", "eta": "03/06 18:00", "hours": 10.0, "available": 180, "capacity": 300, "destination": "汐止調度場", "dest_code": "TPE", "schedule_day": "FRI"}
        ]
    },
    "TPE": {
        "port_name": "汐止調度場",
        "ships": [
            {"name": "EVERGREEN V-301", "name_zh": "長榮虛擬", "voyage": "V301A", "route": "TBS", "etd": "03/03 06:00", "eta": "03/04 06:00", "hours": 24.0, "available": 300, "capacity": 400, "destination": "高雄港", "dest_code": "KHH", "schedule_day": "TUE"},
            {"name": "EVERGREEN V-302", "name_zh": "長榮虛擬", "voyage": "V302A", "route": "TBS", "etd": "03/06 06:00", "eta": "03/07 06:00", "hours": 24.0, "available": 350, "capacity": 400, "destination": "高雄港", "dest_code": "KHH", "schedule_day": "FRI"}
        ]
    }
}