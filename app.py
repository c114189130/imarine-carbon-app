import os
import math
import requests
import random
from datetime import datetime
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

from config import (
    APP_TITLE,
    CERTIFICATE_FILE,
    CARGO_VALUE,
    HISTORY_FILE,
    INTEREST_RATE,
    MAX_HISTORY_RECORDS,
    PORTS,
    PORT_HANDLING_EMISSION_PER_CONTAINER,
    ROAD_SPEED_KMH,
    RISK_COST_RATES,
    SECRET_KEY,
    SEA_SPEED_KMH,
    SOCIAL_COST_OF_CARBON,
    SOCIAL_COST_RATES,
    TRANSPORT_COST_RATES,
    EMISSION_FACTORS,
    TDX_CLIENT_ID,
    TDX_CLIENT_SECRET,
)
from optimization_model import compare_modes, calculate_optimal_transfer_ratio
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.schedule_service import ScheduleService
from services.storage_service import ensure_json_file, read_json, write_json
from services.booking_service import (
    get_available_capacity,
    get_total_capacity,
    book_capacity,
    get_route_summary,
    get_all_ships_summary,
    get_customer_bookings,
    get_upcoming_ships,
    get_booking_summary,
    init_market_simulation
)
from services.carbon_service import get_esg_report
from services.traffic_service import TrafficService

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

schedule_service = ScheduleService()
traffic_service = TrafficService(app_id=TDX_CLIENT_ID, app_key=TDX_CLIENT_SECRET)

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])

# 初始化市場模擬
init_market_simulation()

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
    return read_json(HISTORY_FILE, [])

def save_history(record):
    history = load_history()
    history.append(record)
    history = history[-MAX_HISTORY_RECORDS:]
    write_json(HISTORY_FILE, history)

def load_certificates():
    return read_json(CERTIFICATE_FILE, [])

def save_certificate(certificate):
    rows = load_certificates()
    rows.append(certificate)
    write_json(CERTIFICATE_FILE, rows)

def get_history_record(record_id):
    for record in load_history():
        if record["id"] == record_id:
            return record
    return None

def get_certificate(cert_id):
    for cert in load_certificates():
        if cert["cert_id"] == cert_id:
            return cert
    return None

# ================= 路由 =================
@app.route("/")
def index():
    return render_template("index.html", app_title=APP_TITLE)

@app.route("/history_page")
def history_page():
    return render_template("history.html", app_title=APP_TITLE)

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", app_title=APP_TITLE)

@app.route("/certificate_page")
def certificate_page():
    return render_template("certificate.html", app_title=APP_TITLE)

@app.route("/verify/<cert_id>")
def verify_certificate(cert_id):
    certificate = get_certificate(cert_id)
    return render_template("verify.html", valid=bool(certificate), cert=certificate, app_title=APP_TITLE)

@app.route("/get_history")
def get_history():
    return jsonify(load_history())

@app.route("/api/traffic")
def api_traffic():
    return jsonify(traffic_service.get_live_traffic_speed())

@app.route("/api/ships/<route_key>")
def get_ships(route_key):
    """取得航線所有船班艙位資訊"""
    try:
        ships = get_all_ships_summary(route_key)
        return jsonify(ships)
    except Exception as e:
        print(f"SHIP API ERROR: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500

@app.route("/api/booking-summary")
def booking_summary():
    """取得訂票摘要統計"""
    summary = get_booking_summary()
    return jsonify(summary)

@app.route("/api/bookings")
def get_bookings():
    """取得訂票記錄"""
    company = request.args.get("company")
    if company:
        bookings = get_customer_bookings(company)
    else:
        bookings = get_customer_bookings()
    return jsonify(bookings)

@app.route("/api/book-ship", methods=["POST"])
def book_ship():
    """預訂船班艙位"""
    data = request.get_json()
    route_key = data.get("route_key")
    sailing_date = data.get("sailing_date")
    containers = data.get("containers", 1)
    company_name = data.get("company_name", "")
    cargo_type = data.get("cargo_type", "normal")
    contact_person = data.get("contact_person", "")
    phone = data.get("phone", "")
    
    result = book_capacity(route_key, sailing_date, containers, company_name, cargo_type, contact_person, phone)
    return jsonify(result)

@app.route("/save_history_direct", methods=["POST"])
def save_history_direct():
    """直接保存歷史記錄（用於內陸運輸確認和訂艙）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "無資料"}), 400
        
        # 確保必要欄位存在
        if "id" not in data:
            data["id"] = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
        if "date" not in data:
            data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 確保 savings_amount 有值
        if "savings_amount" not in data or data.get("savings_amount") is None:
            carbon_improvement = data.get("carbon_improvement", 0)
            data["savings_amount"] = round(carbon_improvement * 0.3)
        
        history = load_history()
        history.append(data)
        
        # 保留最近 MAX_HISTORY_RECORDS 筆
        if len(history) > MAX_HISTORY_RECORDS:
            history = history[-MAX_HISTORY_RECORDS:]
        
        write_json(HISTORY_FILE, history)
        return jsonify({"success": True})
    except Exception as e:
        print(f"保存歷史錯誤: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")
    containers = data.get("containers")
    cargo_type = data.get("cargo_type", "normal")
    time_requirement = data.get("time_requirement", 48)

    if start not in PORTS or end not in PORTS:
        return jsonify({"error": "港口代碼無效"}), 400
    if start == end:
        return jsonify({"error": "起點與終點不可相同"}), 400

    try:
        containers = int(containers)
    except (TypeError, ValueError):
        return jsonify({"error": "貨櫃數量格式錯誤"}), 400

    if containers <= 0 or containers > 5000:
        return jsonify({"error": "貨櫃數量需介於 1 到 5000 之間"}), 400

    # 基本距離計算
    p1 = PORTS[start]
    p2 = PORTS[end]
    base_distance = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
    road_distance = estimate_route_distance(base_distance, "road")
    sea_distance = estimate_route_distance(base_distance, "sea")

    # 獲取即時路況
    road_condition = traffic_service.summarize_traffic()
    
    # 獲取船期
    ship_schedule = schedule_service.get_ship_schedule(p1["code"], p2["name"])

    # 計算碳排
    road_carbon = EMISSION_FACTORS["road"] * road_distance * containers
    sea_carbon = EMISSION_FACTORS["sea"] * sea_distance * containers + PORT_HANDLING_EMISSION_PER_CONTAINER * containers * 2

    # 計算成本
    road_freight = TRANSPORT_COST_RATES["road"] * road_distance * containers
    sea_freight = TRANSPORT_COST_RATES["sea"] * sea_distance * containers

    # 計算時間成本
    road_time = calculate_financing_time_cost(road_distance, "road", containers)
    sea_time = calculate_financing_time_cost(sea_distance, "sea", containers)

    # 社會成本
    road_social = SOCIAL_COST_RATES["road"] * road_distance * containers
    sea_social = SOCIAL_COST_RATES["sea"] * sea_distance * containers

    # VSL 風險成本
    road_risk = RISK_COST_RATES["road"] * road_distance * containers
    sea_risk = RISK_COST_RATES["sea"] * sea_distance * containers

    # 碳排外部成本
    road_carbon_externality = road_carbon * SOCIAL_COST_OF_CARBON
    sea_carbon_externality = sea_carbon * SOCIAL_COST_OF_CARBON

    # 總成本
    road_total = road_freight + road_time + road_social + road_risk + road_carbon_externality
    sea_total = sea_freight + sea_time + sea_social + sea_risk + sea_carbon_externality

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

    # 儲存歷史記錄
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
    }
    save_history(record)

    # 回傳結果
    return jsonify({
        "record_id": record["id"],
        "distance": round(base_distance, 2),
        "containers": containers,
        "start_name": p1["name"],
        "end_name": p2["name"],
        "start_lat": p1["lat"],
        "start_lon": p1["lon"],
        "end_lat": p2["lat"],
        "end_lon": p2["lon"],
        "road": {
            "freight": round(road_freight),
            "time": round(road_time),
            "social": round(road_social),
            "risk": round(road_risk),
            "carbon": round(road_carbon, 2),
            "total": round(road_total),
        },
        "sea": {
            "freight": round(sea_freight),
            "time": round(sea_time),
            "social": round(sea_social),
            "risk": round(sea_risk),
            "carbon": round(sea_carbon, 2),
            "total": round(sea_total),
        },
        "best_mode": best_mode,
        "social_savings": round(social_savings),
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "recommendation": f"選擇 {best_mode} 可減少 {carbon_improvement:.0f} kg CO2e，約 {reduction_pct:.1f}%",
        "road_condition": {
            "level": road_condition["level"],
            "level_text": "🟢 順暢" if road_condition["level"] == "low" else "🟡 車多" if road_condition["level"] == "medium" else "🔴 壅塞",
            "avg_speed": road_condition["avg_speed"],
        },
        "ship_schedule": ship_schedule,
    })

@app.route("/certificate", methods=["POST"])
def create_certificate():
    data = request.get_json(silent=True) or {}
    record_id = data.get("record_id")
    company_name = (data.get("company_name") or "").strip()

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
        "record": record,
    }
    save_certificate(certificate)

    return jsonify({
        "cert_id": cert_id,
        "company_name": company_name,
        "issued_at": certificate["issued_at"],
        "route": f"{record['start']} → {record['end']}",
        "containers": record["containers"],
        "carbon_improvement": record["carbon_improvement"],
        "reduction_pct": record["reduction_pct"],
    })

@app.route("/download_certificate/<cert_id>/<lang>")
def download_certificate(cert_id, lang):
    certificate = get_certificate(cert_id)
    if not certificate:
        return jsonify({"error": "查無證書"}), 404

    lang = "en" if lang == "en" else "zh"
    pdf_buffer = build_certificate_pdf(certificate, lang=lang)
    filename = f"certificate_{cert_id}_{'english' if lang == 'en' else 'chinese'}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)