# 應用程式標題
APP_TITLE = "iMarine 智慧海運碳排管理平台"

# 檔案路徑
HISTORY_FILE = "history.json"
CERTIFICATE_FILE = "certificates.json"

# 貨物價值 (NTD)
CARGO_VALUE = 5000000

# 年利率 (%)
INTEREST_RATE = 0.05

# 最大歷史記錄筆數
MAX_HISTORY_RECORDS = 200

# 運輸速度 (km/h)
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 30

# 港口資訊
PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.6163, "lon": 120.2833, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.2833, "lon": 120.5167, "code": "TXG"},
    "taipei": {"name": "台北港", "lat": 25.1500, "lon": 121.3833, "code": "TPE"},
}

# 港口處理碳排放 (kg/櫃)
PORT_HANDLING_EMISSION_PER_CONTAINER = 10

# 碳的社會成本 (NTD/kg)
SOCIAL_COST_OF_CARBON = 0.5

# 社會成本費率 (NTD/km/櫃)
SOCIAL_COST_RATES = {
    "road": 0.5,
    "sea": 0.2
}

# 風險成本費率 (NTD/km/櫃)
RISK_COST_RATES = {
    "road": 1.2,
    "sea": 0.3
}

# 運輸成本費率 (NTD/km/櫃)
TRANSPORT_COST_RATES = {
    "road": 33.5,
    "sea": 12.9
}

# 碳排係數 (kg CO2e/km/櫃)
EMISSION_FACTORS = {
    "road": 2.925,
    "sea": 0.675
}

# 碳費價格 (NTD/kg)
CARBON_FEE_RATE = 0.3

# 碳權價格 (NTD/kg)
CARBON_CREDIT_RATE = 0.32

# SECRET KEY
SECRET_KEY = "your-secret-key-here-change-in-production"

# TDX API 憑證 (選用)
TDX_CLIENT_ID = ""
TDX_CLIENT_SECRET = ""