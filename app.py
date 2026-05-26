import os
import math
import json
import random
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
CARGO_VALUE = 5000000
INTEREST_RATE = 0.05
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 25
TRANSPORT_COST_RATES = {"road": 33.5, "sea": 12.8}
EMISSION_FACTORS = {"road": 0.062, "sea": 0.018}
SOCIAL_COST_RATES = {"road": 8.5, "sea": 3.2}
RISK_COST_RATES = {"road": 12.0, "sea": 5.5}
PORT_HANDLING_EMISSION_PER_CONTAINER = 15
SOCIAL_COST_OF_CARBON = 0.39
CARBON_PRICE = 0.3

# 固定成本
SEA_COST_PER_FEU = 2787
ROAD_COST_PER_FEU = 7218
DISTANCE_KM = 215
SEA_TRANSIT_DAYS = 5
ROAD_TRANSIT_DAYS = 1

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
    {"voyage": "0735-519B", "sailing_date": "2026-07-02", "kaohsiung": "07/02", "taichung": "07/04", "taipei": "07/07"},
    {"voyage": "0736-520B", "sailing_date": "2026-07-09", "kaohsiung": "07/09", "taichung": "07/11", "taipei": "07/14"},
    {"voyage": "0737-521B", "sailing_date": "2026-07-16", "kaohsiung": "07/16", "taichung": "07/18", "taipei": "07/21"},
    {"voyage": "0738-522B", "sailing_date": "2026-07-23", "kaohsiung": "07/23", "taichung": "07/25", "taipei": "07/28"},
    {"voyage": "0739-523B", "sailing_date": "2026-07-30", "kaohsiung": "07/30", "taichung": "08/01", "taipei": "08/04"},
    {"voyage": "0740-524B", "sailing_date": "2026-08-06", "kaohsiung": "08/06", "taichung": "08/08", "taipei": "08/11"},
    {"voyage": "0741-525B", "sailing_date": "2026-08-13", "kaohsiung": "08/13", "taichung": "08/15", "taipei": "08/18"},
    {"voyage": "0742-526B", "sailing_date": "2026-08-20", "kaohsiung": "08/20", "taichung": "08/22", "taipei": "08/25"},
    {"voyage": "0743-527B", "sailing_date": "2026-08-27", "kaohsiung": "08/27", "taichung": "08/29", "taipei": "09/01"},
    {"voyage": "0744-528B", "sailing_date": "2026-09-03", "kaohsiung": "09/03", "taichung": "09/05", "taipei": "09/08"},
    {"voyage": "0745-529B", "sailing_date": "2026-09-10", "kaohsiung": "09/10", "taichung": "09/12", "taipei": "09/14"}
]

# ================= 輔助函數 =================
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def estimate_route_distance(base_distance_km, mode):
    multiplier = 1.22 if mode == "road" else 1.08
    return round(base_distance_km * multiplier, 2)

def calculate_financing_time_cost(distance_km, mode, containers, time_sensitivity=0.3):
    hours = distance_km / (ROAD_SPEED_KMH if mode == "road" else SEA_SPEED_KMH)
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history_record(record):
    history = load_history()
    history.append(record)
    if len(history) > MAX_HISTORY_RECORDS:
        history = history[-MAX_HISTORY_RECORDS:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_certificates():
    if os.path.exists(CERTIFICATE_FILE):
        with open(CERTIFICATE_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_certificate(certificate):
    certificates = load_certificates()
    certificates.append(certificate)
    with open(CERTIFICATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(certificates, f, ensure_ascii=False, indent=2)

def get_history_record(record_id):
    for record in load_history():
        if record.get("id") == record_id:
            return record
    return None

def generate_certificate_id():
    return f"CERT-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

# ================= 頁面路由 =================
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

# ================= API：即時路況 =================
@app.route('/api/traffic')
def api_traffic():
    roads = [
        {"road": "國道1號", "speed": random.randint(40, 95)},
        {"road": "國道3號", "speed": random.randint(45, 100)},
        {"road": "台61線", "speed": random.randint(50, 90)},
        {"road": "台17線", "speed": random.randint(35, 70)}
    ]
    return jsonify(roads)

# ================= API：船班資料 =================
@app.route('/api/ships/<route_key>')
def api_ships(route_key):
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
    try:
        data = request.get_json()
        start = data.get('start', 'kaohsiung')
        end = data.get('end', 'taichung')
        containers = int(data.get('containers', 50))
        cargo_type = data.get('cargo_type', 'normal')
        departure_date = data.get('departure_date', datetime.now().strftime("%Y-%m-%d"))
        arrival_requirement = data.get('arrival_requirement', "")
        
        p1 = PORTS.get(start, PORTS['kaohsiung'])
        p2 = PORTS.get(end, PORTS['taichung'])
        
        base_distance = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
        road_distance = estimate_route_distance(base_distance, "road")
        sea_distance = estimate_route_distance(base_distance, "sea")
        
        road_carbon = EMISSION_FACTORS["road"] * road_distance * containers
        sea_carbon = EMISSION_FACTORS["sea"] * sea_distance * containers + PORT_HANDLING_EMISSION_PER_CONTAINER * containers * 2
        
        road_freight = TRANSPORT_COST_RATES["road"] * road_distance * containers
        sea_freight = TRANSPORT_COST_RATES["sea"] * sea_distance * containers
        
        road_time_cost = calculate_financing_time_cost(road_distance, "road", containers)
        sea_time_cost = calculate_financing_time_cost(sea_distance, "sea", containers)
        
        road_social = SOCIAL_COST_RATES["road"] * road_distance * containers
        sea_social = SOCIAL_COST_RATES["sea"] * sea_distance * containers
        
        road_risk = RISK_COST_RATES["road"] * road_distance * containers
        sea_risk = RISK_COST_RATES["sea"] * sea_distance * containers
        
        road_carbon_externality = road_carbon * SOCIAL_COST_OF_CARBON
        sea_carbon_externality = sea_carbon * SOCIAL_COST_OF_CARBON
        
        road_total = road_freight + road_time_cost + road_social + road_risk + road_carbon_externality
        sea_total = sea_freight + sea_time_cost + sea_social + sea_risk + sea_carbon_externality
        
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
        
        record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start": p1["name"],
            "end": p2["name"],
            "containers": containers,
            "cargo_type": cargo_type,
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
            "road_arrival_date": road_arrival,
            "departure_date": departure_date,
            "arrival_requirement": arrival_requirement
        }
        save_history_record(record)
        
        return jsonify({
            "success": True,
            "record_id": record["id"],
            "distance": round(base_distance, 2),
            "containers": containers,
            "start_name": p1["name"],
            "end_name": p2["name"],
            "road": {
                "freight": round(road_freight),
                "time_cost": round(road_time_cost),
                "social": round(road_social),
                "risk": round(road_risk),
                "carbon": round(road_carbon, 2),
                "total": round(road_total),
                "arrival_date": road_arrival
            },
            "sea": {
                "freight": round(sea_freight),
                "time_cost": round(sea_time_cost),
                "social": round(sea_social),
                "risk": round(sea_risk),
                "carbon": round(sea_carbon, 2),
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
    try:
        data = request.get_json()
        
        route_key = data.get('route_key')
        sailing_date = data.get('sailing_date')
        containers = int(data.get('containers', 1))
        company_name = data.get('company_name', '')
        cargo_type = data.get('cargo_type', 'normal')
        contact_person = data.get('contact_person', '')
        phone = data.get('phone', '')
        
        ship_info = None
        for s in REAL_SHIP_SCHEDULE:
            if s["sailing_date"] == sailing_date:
                ship_info = s
                break
        
        if not ship_info:
            ship_info = {"voyage": "未知", "sailing_date": sailing_date}
        
        total_price = containers * SEA_COST_PER_FEU
        road_carbon = EMISSION_FACTORS["road"] * DISTANCE_KM * containers
        sea_carbon = EMISSION_FACTORS["sea"] * DISTANCE_KM * containers
        carbon_saved = road_carbon - sea_carbon
        cost_saved = (ROAD_COST_PER_FEU - SEA_COST_PER_FEU) * containers
        
        booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        
        start_name = "高雄港" if "KHH" in route_key else "台中港"
        end_name = "台中港" if "KHH" in route_key else "高雄港"
        sea_arrival = (datetime.strptime(sailing_date, "%Y-%m-%d") + timedelta(days=SEA_TRANSIT_DAYS)).strftime("%Y-%m-%d")
        
        history_record = {
            "id": booking_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start": start_name,
            "end": end_name,
            "containers": containers,
            "cargo_type": cargo_type,
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
            "ship_date": sailing_date,
            "voyage_no": ship_info["voyage"],
            "contact_person": contact_person,
            "phone": phone,
            "sea_arrival_date": sea_arrival,
            "departure_date": sailing_date,
            "road_total": 0,
            "sea_total": total_price
        }
        save_history_record(history_record)
        
        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "containers": containers,
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
    history = load_history()
    history.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(history)

# ================= API：訂艙統計摘要 =================
@app.route('/api/booking-summary')
def booking_summary():
    history = load_history()
    
    total_bookings = len(history)
    total_containers = sum(h.get('containers', 0) for h in history)
    total_revenue = sum(h.get('sea_total', 0) for h in history if h.get('best_mode') == '海運')
    total_carbon_saved = sum(h.get('carbon_improvement', 0) for h in history)
    total_cost_saved = sum(h.get('savings_amount', 0) for h in history)
    
    sea_count = sum(1 for h in history if h.get('best_mode') == '海運')
    sea_rate = round((sea_count / total_bookings) * 100, 1) if total_bookings > 0 else 0
    
    return jsonify({
        "total_bookings": total_bookings,
        "total_containers": total_containers,
        "total_revenue": total_revenue,
        "total_carbon_saved": round(total_carbon_saved, 2),
        "total_cost_saved": round(total_cost_saved, 2),
        "sea_rate": sea_rate,
        "avg_containers": round(total_containers / total_bookings, 1) if total_bookings > 0 else 0
    })

# ================= API：證書 =================
@app.route('/certificate', methods=['POST'])
def create_certificate():
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
            "carbon_improvement": record["carbon_improvement"],
            "reduction_pct": record.get("reduction_pct", 0)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ================= 啟動 =================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)