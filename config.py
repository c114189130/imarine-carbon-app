from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(exist_ok=True)

APP_TITLE = "iMarine 智慧海運碳排管理系統"
SECRET_KEY = "change-me-in-production"

EMISSION_FACTORS = {
    "road": 0.06,
    "sea": 0.02,
}

TRANSPORT_COST_RATES = {
    "road": 60,
    "sea": 24,
}

RISK_COST_RATES = {
    "road": 1.36,
    "sea": 0.18,
}

SOCIAL_COST_RATES = {
    "road": 3.70,
    "sea": 0.64,
}

SOCIAL_COST_OF_CARBON = 10.0
TIME_VALUE_PER_HOUR = 57
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 46
PORT_HANDLING_EMISSION_PER_CONTAINER = 8.0
CARGO_VALUE = 10_000_000
INTEREST_RATE = 0.05
MAX_HISTORY_RECORDS = 200

PORTS = {
    "kaohsiung": {
        "name": "高雄港",
        "lat": 22.616,
        "lon": 120.300,
        "code": "KHH",
    },
    "taichung": {
        "name": "台中港",
        "lat": 24.270,
        "lon": 120.520,
        "code": "TXG",
    },
}

HISTORY_FILE = DATA_DIR / "history.json"
CERTIFICATE_FILE = DATA_DIR / "certificates.json"
SCHEDULE_FILE = DATA_DIR / "evergreen_schedule.json"

DEFAULT_SCHEDULE = {
    "KHH": {
        "port_name": "高雄港",
        "ships": [
            {
                "name": "Evergreen TBS2",
                "eta_hours": 18,
                "available": 320,
                "destination": "台中港",
                "route": "TBS2",
                "eta": "FRI",
            }
        ],
    },
    "TXG": {
        "port_name": "台中港",
        "ships": [
            {
                "name": "Evergreen TBS",
                "eta_hours": 24,
                "available": 560,
                "destination": "高雄港",
                "route": "TBS",
                "eta": "THU",
            }
        ],
    },
}