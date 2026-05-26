import os
import math
import json
import random
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

# ================= 設定 =================
APP_TITLE = "iMarine 智慧海運碳排管理平台"
HISTORY_FILE = "history.json"
CERTIFICATE_FILE = "certificates.json"
MAX_HISTORY_RECORDS = 200

# 港口資料
PORTS = {
    "kaohsiung": {"name": "高雄港", "lat": 22.6163, "lon": 120.2682, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.2667, "lon": 120.5333, "code": "TXG"},
    "taipei": {"name": "台北港", "lat": 25.1500, "lon": 121.4000, "code": "TPE"}
}

# 運輸參數
CARGO_VALUE = 5000000  # 貨物價值 (NTD/櫃)
INTEREST_RATE = 0.05   # 年利率
ROAD_SPEED_KMH = 60    # 公路速度
SEA_SPEED_KMH = 25     # 海運速度

# 運輸成本費率 (NTD/km/櫃)
TRANSPORT_COST_RATES = {
    "road": 33.5,
    "sea": 12.8
}

# 碳排係數 (kg CO2e/km/櫃)
EMISSION_FACTORS = {
    "road": 0.062,
    "sea": 0.018
}

# 社會成本費率 (NTD/km/櫃)
SOCIAL_COST_RATES = {
    "road": 8.5,
    "sea": 3.2
}

# 風險成本費率 (NTD/km/櫃)
RISK_COST_RATES = {
    "road": 12.0,
    "sea": 5.5
}

# 港口裝卸碳排 (kg CO2e/櫃)
PORT_HANDLING_EMISSION_PER_CONTAINER = 15

# 碳的社會成本 (NTD/kg CO2e)
SOCIAL_COST_OF_CARBON = 0.39

# 碳權價格 (NTD/kg)
CARBON_PRICE = 0.3

# 運輸天數
SEA_TRANSIT_DAYS = 5
ROAD_TRANSIT_DAYS = 1
DISTANCE_KM = 215

# 每櫃成本 (以40呎為基準)
SEA_COST_PER_FEU = 2787
ROAD_COST_PER_FEU = 7218

# 貨櫃尺寸換算係數 (以40呎為基準 = 1)
CONTAINER_SIZE_FACTOR = {
    "normal_20": 0.5,   # 20呎 = 0.5 個標準櫃
    "normal_40": 1.0,   # 40呎 = 1.0 個標準櫃
    "dangerous": 1.0    # 危險品以40呎計算
}

# 貨櫃尺寸名稱對照
CONTAINER_SIZE_NAME = {
    "normal_20": "20呎",
    "normal_40": "40呎",
    "dangerous": "危險品"
}

# 人命價值 VSL 階段 (NTD)
VSL_STAGES = {
    10: 408700, 15: 613050, 20: 817400, 25: 1021750, 30: 1226100,
    35: 1430450, 40: 1634800, 45: 1839150, 50: 2043500, 55: 2247850,
    60: 2452200, 65: 2656550, 70: 2860900, 75: 3065250, 80: 3269600,
    85: 3473950, 90: 3678300, 95: 3882650
}

# 真實船期資料
REAL_SHIP_SCHEDULE = [
    {"voyage": "0727-511B", "sailing_date": "2026-05-07", "kaohsiung": "05/07", "taichung": "05/08", "taipei": "05/12"},
    {"voyage": "0728-512B", "sailing_date": "2026-05-13", "kaohsiung": "05/13", "taichung": "05/14", "taipei": "05/19"},
    {"voyage": "0729-513B", "sailing_date": "2026-05-20", "kaohsiung": "05/20", "taichung": "05/21", "taipei": "05/26"},
    {"voyage": "0730-514B", "sailing_date": "2026-05-27", "kaohsiung": "05/27", "taichung": "05/28", "taipei": "06/01"},
    {"voyage": "0731-515B", "sailing_date": "2026-06-03", "kaohsiung": "06/03", "taichung": "06/04", "taipei": "06/09"},
    {"voyage": "0732-516B", "sailing_date": "2026-06-10", "kaohsiung": "06/10", "taichung": "06/12", "taipei": "06/16"},
    {"voyage": "0733-517B", "sailing_date": "2026-06-17", "kaohsiung": "06/17", "taichung": "06/19", "taipei": "06/23"},
    {"voyage": "0734-518B", "sailing_date": "2026-06-25", "kaohsiung": "06/25", "taichung": "06/26", "taipei": "06/30"},
    {"voyage": "0735-519B", "sailing_date": "2026-07-02", "kaohsiung": "07/02", "taichung": "07/04", "taipei": "07/07"}
]

# ================= 輔助函數 =================
def get_container_factor(cargo_type):
    """取得貨櫃尺寸換算係數"""
    return CONTAINER_SIZE_FACTOR.get(cargo_type, 1.0)

def get_container_size_name(cargo_type):
    """取得貨櫃尺寸名稱"""
    return CONTAINER_SIZE_NAME.get(cargo_type, "標準櫃")

def get_actual_containers(containers, cargo_type):
    """根據貨物類型換算實際標準櫃數量 (以40呎為基準)"""
    factor = get_container_factor(cargo_type)
    return containers * factor

def haversine_distance(lat1, lon1, lat2, lon2):
    """計算兩點之間的球面距離 (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def estimate_route_distance(base_distance_km, mode):
    """估算實際運輸距離"""
    multiplier = 1.22 if mode == "road" else 1.08
    return round(base_distance_km * multiplier, 2)

def calculate_financing_time_cost(distance_km, mode, containers, time_sensitivity=0.3):
    """計算在途資金成本"""
    hours = distance_km / (ROAD_SPEED_KMH if mode == "road" else SEA_SPEED_KMH)
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier

def get_vsl_by_utilization(utilization):
    """根據艙位使用率取得 VSL 值"""
    keys = sorted(VSL_STAGES.keys())
    closest = keys[0]
    for k in keys:
        if k <= utilization:
            closest = k
    return VSL_STAGES[closest]

def load_history():
    """載入歷史記錄"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history_record(record):
    """儲存歷史記錄"""
    history = load_history()
    history.append(record)
    if len(history) > MAX_HISTORY_RECORDS:
        history = history[-MAX_HISTORY_RECORDS:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_certificates():
    """載入證書"""
    if os.path.exists(CERTIFICATE_FILE):
        with open(CERTIFICATE_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_certificate(certificate):
    """儲存證書"""
    certificates = load_certificates()
    certificates.append(certificate)
    with open(CERTIFICATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(certificates, f, ensure_ascii=False, indent=2)

def get_history_record(record_id):
    """根據 ID 取得歷史記錄"""
    for record in load_history():
        if record.get("id") == record_id:
            return record
    return None

def get_certificate(cert_id):
    """根據證書 ID 取得證書"""
    for cert in load_certificates():
        if cert.get("cert_id") == cert_id:
            return cert
    return None

def generate_certificate_id():
    """產生證書編號"""
    return f"CERT-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

# ================= 路由 =================
@app.route('/')
def index():
    return render_template('index.html', app_title=APP_TITLE)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', app_title=APP_TITLE)

@app.route('/history_page')
def history_page():
    return render_template('history.html', app_title=APP_TITLE)

@app.route('/certificate_page')
def certificate_page():
    return render_template('certificate.html', app_title=APP_TITLE)

@app.route('/verify/<cert_id>')
def verify_certificate(cert_id):
    certificate = get_certificate(cert_id)
    return render_template('verify.html', valid=bool(certificate), cert=certificate, app_title=APP_TITLE)

# ================= API：即時路況 =================
@app.route('/api/traffic')
def api_traffic():
    """模擬即時路況資料"""
    roads = [
        {"road": "國道1號", "speed": random.randint(40, 95), "congestion": random.choice(["順暢", "車多", "壅塞"])},
        {"road": "國道3號", "speed": random.randint(45, 100), "congestion": random.choice(["順暢", "車多", "壅塞"])},
        {"road": "台61線", "speed": random.randint(50, 90), "congestion": random.choice(["順暢", "車多", "壅塞"])},
        {"road": "台17線", "speed": random.randint(35, 70), "congestion": random.choice(["順暢", "車多", "壅塞"])}
    ]
    return jsonify(roads)

# ================= API：船班資料 =================
@app.route('/api/ships/<route_key>')
def api_ships(route_key):
    """根據航線回傳船班資料"""
    today = datetime.now().strftime("%Y-%m-%d")
    ships = []
    
    for s in REAL_SHIP_SCHEDULE:
        if s["sailing_date"] >= today:
            utilization = random.randint(20, 95)
            capacity = 1618
            remaining = int(capacity * (1 - utilization/100))
            price_multiplier = 1 + (utilization - 50) / 100
            dynamic_price = int(SEA_COST_PER_FEU * price_multiplier)
            
            ships.append({
                "ship_name": "UNI-PROSPER",
                "voyage_no": s["voyage"],
                "sailing_date": s["sailing_date"],
                "capacity": capacity,
                "remaining": max(0, remaining),
                "utilization": utilization,
                "dynamic_price": max(SEA_COST_PER_FEU, dynamic_price),
                "route": route_key
            })
    
    ships.sort(key=lambda x: x["sailing_date"])
    return jsonify(ships)

# ================= API：碳排計算 =================
@app.route('/calculate', methods=['POST'])
def calculate():
    """計算碳排和成本比較"""
    try:
        data = request.get_json()
        start = data.get('start', 'kaohsiung')
        end = data.get('end', 'taichung')
        containers = int(data.get('containers', 50))
        cargo_type = data.get('cargo_type', 'normal_40')
        departure_date = data.get('departure_date', datetime.now().strftime("%Y-%m-%d"))
        
        # 換算實際標準櫃數量
        actual_containers = get_actual_containers(containers, cargo_type)
        container_size_name = get_container_size_name(cargo_type)
        
        # 獲取港口資訊
        p1 = PORTS.get(start, PORTS['kaohsiung'])
        p2 = PORTS.get(end, PORTS['taichung'])
        
        # 計算距離
        base_distance = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
        road_distance = estimate_route_distance(base_distance, "road")
        sea_distance = estimate_route_distance(base_distance, "sea")
        
        # 計算碳排 (使用實際標準櫃數量)
        road_carbon = EMISSION_FACTORS["road"] * road_distance * actual_containers
        sea_carbon = EMISSION_FACTORS["sea"] * sea_distance * actual_containers + PORT_HANDLING_EMISSION_PER_CONTAINER * actual_containers * 2
        
        # 計算成本
        road_freight = TRANSPORT_COST_RATES["road"] * road_distance * actual_containers
        sea_freight = TRANSPORT_COST_RATES["sea"] * sea_distance * actual_containers
        
        # 計算時間成本
        road_time_cost = calculate_financing_time_cost(road_distance, "road", actual_containers)
        sea_time_cost = calculate_financing_time_cost(sea_distance, "sea", actual_containers)
        
        # 社會成本
        road_social = SOCIAL_COST_RATES["road"] * road_distance * actual_containers
        sea_social = SOCIAL_COST_RATES["sea"] * sea_distance * actual_containers
        
        # 風險成本
        road_risk = RISK_COST_RATES["road"] * road_distance * actual_containers
        sea_risk = RISK_COST_RATES["sea"] * sea_distance * actual_containers
        
        # 碳排外部成本
        road_carbon_externality = road_carbon * SOCIAL_COST_OF_CARBON
        sea_carbon_externality = sea_carbon * SOCIAL_COST_OF_CARBON
        
        # 總成本
        road_total = road_freight + road_time_cost + road_social + road_risk + road_carbon_externality
        sea_total = sea_freight + sea_time_cost + sea_social + sea_risk + sea_carbon_externality
        
        # 決定最佳方案
        if sea_total < road_total:
            best_mode = "海運"
            social_savings = road_total - sea_total
            carbon_improvement = road_carbon - sea_carbon
            baseline = road_carbon
            savings_amount = road_total - sea_total
        else:
            best_mode = "公路"
            social_savings = sea_total - road_total
            carbon_improvement = sea_carbon - road_carbon
            baseline = sea_carbon
            savings_amount = 0
        
        reduction_pct = (carbon_improvement / baseline * 100) if baseline > 0 else 0
        
        # 計算抵達日期
        sea_arrival = (datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(days=SEA_TRANSIT_DAYS)).strftime("%Y-%m-%d")
        road_arrival = (datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(days=ROAD_TRANSIT_DAYS)).strftime("%Y-%m-%d")
        
        # 儲存歷史記錄
        record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start": p1["name"],
            "end": p2["name"],
            "containers": containers,
            "container_size": container_size_name,
            "cargo_type": cargo_type,
            "actual_containers": round(actual_containers, 2),
            "base_distance": round(base_distance, 2),
            "road_carbon": round(road_carbon, 2),
            "sea_carbon": round(sea_carbon, 2),
            "carbon_improvement": round(carbon_improvement, 2),
            "reduction_pct": round(reduction_pct, 1),
            "best_mode": best_mode,
            "social_savings": round(social_savings),
            "savings_amount": round(savings_amount),
            "road_total": round(road_total),
            "sea_total": round(sea_total),
            "sea_arrival_date": sea_arrival,
            "road_arrival_date": road_arrival
        }
        save_history_record(record)
        
        return jsonify({
            "success": True,
            "record_id": record["id"],
            "distance": round(base_distance, 2),
            "containers": containers,
            "container_size": container_size_name,
            "actual_containers": round(actual_containers, 2),
            "start_name": p1["name"],
            "end_name": p2["name"],
            "road": {
                "freight": round(road_freight),
                "time_cost": round(road_time_cost),
                "social": round(road_social),
                "risk": round(road_risk),
                "carbon": round(road_carbon, 2),
                "carbon_externality": round(road_carbon_externality),
                "total": round(road_total),
                "arrival_date": road_arrival
            },
            "sea": {
                "freight": round(sea_freight),
                "time_cost": round(sea_time_cost),
                "social": round(sea_social),
                "risk": round(sea_risk),
                "carbon": round(sea_carbon, 2),
                "carbon_externality": round(sea_carbon_externality),
                "total": round(sea_total),
                "arrival_date": sea_arrival
            },
            "best_mode": best_mode,
            "social_savings": round(social_savings),
            "carbon_improvement": round(carbon_improvement, 2),
            "reduction_pct": round(reduction_pct, 1),
            "recommendation": f"選擇 {best_mode} 可減少 {carbon_improvement:.0f} kg CO2e，約 {reduction_pct:.1f}%"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ================= API：訂艙 =================
@app.route('/api/book-ship', methods=['POST'])
def api_book_ship():
    """處理訂艙請求"""
    try:
        data = request.get_json()
        
        route_key = data.get('route_key')
        sailing_date = data.get('sailing_date')
        containers = int(data.get('containers', 1))
        company_name = data.get('company_name', '')
        cargo_type = data.get('cargo_type', 'normal_40')
        contact_person = data.get('contact_person', '')
        phone = data.get('phone', '')
        
        # 換算實際標準櫃數量
        actual_containers = get_actual_containers(containers, cargo_type)
        container_size_name = get_container_size_name(cargo_type)
        
        # 找到對應的船班
        ship_info = None
        for s in REAL_SHIP_SCHEDULE:
            if s["sailing_date"] == sailing_date:
                ship_info = s
                break
        
        if not ship_info:
            ship_info = {"voyage": "未知", "sailing_date": sailing_date}
        
        # 計算總價 (使用實際標準櫃數量)
        total_price = int(SEA_COST_PER_FEU * actual_containers)
        
        # 計算減碳量
        road_carbon = EMISSION_FACTORS["road"] * DISTANCE_KM * actual_containers
        sea_carbon = EMISSION_FACTORS["sea"] * DISTANCE_KM * actual_containers
        carbon_saved = road_carbon - sea_carbon
        cost_saved = (ROAD_COST_PER_FEU - SEA_COST_PER_FEU) * actual_containers
        
        # 產生訂單編號
        booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        
        # 儲存到歷史記錄
        start_name = "高雄港" if "KHH" in route_key else "台中港"
        end_name = "台中港" if "KHH" in route_key else "高雄港"
        
        history_record = {
            "id": booking_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start": start_name,
            "end": end_name,
            "containers": containers,
            "container_size": container_size_name,
            "cargo_type": cargo_type,
            "actual_containers": round(actual_containers, 2),
            "base_distance": DISTANCE_KM,
            "road_carbon": round(road_carbon, 2),
            "sea_carbon": round(sea_carbon, 2),
            "carbon_improvement": round(carbon_saved, 2),
            "reduction_pct": round((carbon_saved / road_carbon) * 100, 1) if road_carbon > 0 else 0,
            "savings_amount": round(cost_saved, 2),
            "best_mode": "海運",
            "company_name": company_name,
            "booking_id": booking_id,
            "sailing_date": sailing_date,
            "voyage_no": ship_info["voyage"]
        }
        save_history_record(history_record)
        
        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "containers": containers,
            "container_size": container_size_name,
            "actual_containers": round(actual_containers, 2),
            "ship_name": "UNI-PROSPER",
            "voyage_no": ship_info["voyage"],
            "sailing_date": sailing_date,
            "total_price": total_price,
            "carbon_saved": round(carbon_saved, 2),
            "cost_saved": round(cost_saved, 2)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ================= API：保存歷史記錄 =================
@app.route('/save_history_direct', methods=['POST'])
def save_history_direct():
    """直接保存歷史記錄（用於內陸運輸確認）"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "無資料"}), 400
        
        if 'id' not in data:
            data['id'] = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
        if 'date' not in data:
            data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'savings_amount' not in data or data.get('savings_amount') is None:
            carbon_improvement = data.get('carbon_improvement', 0)
            data['savings_amount'] = round(carbon_improvement * CARBON_PRICE, 2)
        
        save_history_record(data)
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"保存歷史錯誤: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ================= API：取得歷史記錄 =================
@app.route('/get_history')
def get_history():
    """取得所有歷史記錄"""
    history = load_history()
    history.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(history)

# ================= API：訂艙統計摘要 =================
@app.route('/api/booking-summary')
def booking_summary():
    """取得訂艙統計摘要"""
    history = load_history()
    
    total_bookings = len(history)
    total_containers = sum(h.get('containers', 0) for h in history)
    total_actual_containers = sum(h.get('actual_containers', h.get('containers', 0)) for h in history)
    total_revenue = sum(h.get('sea_total', 0) for h in history if h.get('best_mode') == '海運')
    total_carbon_saved = sum(h.get('carbon_improvement', 0) for h in history)
    total_cost_saved = sum(h.get('savings_amount', 0) for h in history)
    
    sea_count = sum(1 for h in history if h.get('best_mode') == '海運')
    sea_rate = round((sea_count / total_bookings) * 100, 1) if total_bookings > 0 else 0
    
    return jsonify({
        "total_bookings": total_bookings,
        "total_containers": total_containers,
        "total_actual_containers": round(total_actual_containers, 2),
        "total_revenue": total_revenue,
        "total_carbon_saved": round(total_carbon_saved, 2),
        "total_cost_saved": round(total_cost_saved, 2),
        "sea_rate": sea_rate,
        "avg_containers": round(total_containers / total_bookings, 1) if total_bookings > 0 else 0
    })

# ================= API：證書 =================
@app.route('/certificate', methods=['POST'])
def create_certificate():
    """建立減碳證書"""
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return jsonify({"error": "請輸入公司名稱"}), 400
        if not record_id:
            return jsonify({"error": "缺少計算紀錄 ID"}), 400
        
        record = get_history_record(record_id)
        if not record:
            return jsonify({"error": "查無對應的計算紀錄"}), 404
        
        cert_id = generate_certificate_id()
        certificate = {
            "cert_id": cert_id,
            "company_name": company_name,
            "issued_at": datetime.now().strftime("%Y-%m-%d"),
            "record_id": record_id,
            "record": record
        }
        save_certificate(certificate)
        
        return jsonify({
            "success": True,
            "cert_id": cert_id,
            "company_name": company_name,
            "issued_at": certificate["issued_at"],
            "route": f"{record['start']} → {record['end']}",
            "containers": record["containers"],
            "container_size": record.get("container_size", "40呎"),
            "carbon_improvement": record["carbon_improvement"],
            "reduction_pct": record.get("reduction_pct", 0)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ================= 啟動伺服器 =================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)