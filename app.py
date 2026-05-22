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
from services.certificate_service import build_certificate_pdf, build_certificate_pdf_report, generate_certificate_id
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
    """取得即時路況 - 模擬資料（因為 TDX API 可能需要認證）"""
    try:
        # 模擬即時路況數據
        import random
        current_hour = datetime.now().hour
        
        # 根據時間模擬不同路況
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            # 尖峰時段
            speeds = [random.randint(30, 50) for _ in range(5)]
            level = "medium"
        elif 11 <= current_hour <= 13:
            # 中午時段
            speeds = [random.randint(50, 70) for _ in range(5)]
            level = "low"
        else:
            # 離峰時段
            speeds = [random.randint(60, 90) for _ in range(5)]
            level = "low"
        
        return jsonify([
            {"road": f"國道{num}號", "speed": speeds[i], "level": level}
            for i, num in enumerate([1, 3, 5, 10, 18])
        ])
    except Exception as e:
        print(f"路況 API 錯誤: {e}")
        # 返回模擬數據
        return jsonify([
            {"road": "國道1號", "speed": 65, "level": "low"},
            {"road": "國道3號", "speed": 70, "level": "low"},
            {"road": "國道5號", "speed": 60, "level": "low"},
            {"road": "國道10號", "speed": 75, "level": "low"},
            {"road": "國道18號", "speed": 68, "level": "low"},
        ])

@app.route("/api/ships/<route_key>")
def get_ships(route_key):
    """取得航線所有船班艙位資訊 - 模擬資料"""
    try:
        # 模擬船班資料
        import random
        from datetime import datetime, timedelta
        
        ships = []
        today = datetime.now()
        
        # 模擬未來幾週的船班
        for i in range(1, 5):
            sailing_date = today + timedelta(days=i*7)
            # 模擬使用率在 20% 到 90% 之間
            utilization = random.randint(20, 90)
            remaining = int(500 * (1 - utilization / 100))
            
            ships.append({
                "ship_name": "UNI-PROSPER",
                "voyage_no": f"072{i+2}-51{i+1}B",
                "sailing_date": sailing_date.strftime("%Y-%m-%d"),
                "capacity": 500,
                "remaining": remaining,
                "utilization": utilization,
                "dynamic_price": 12000 + random.randint(-500, 1000),
                "route": route_key
            })
        
        return jsonify(ships)
    except Exception as e:
        print(f"SHIP API ERROR: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500

@app.route("/api/booking-summary")
def booking_summary():
    """取得訂票摘要統計 - 從歷史記錄計算"""
    try:
        history = load_history()
        
        # 只計算海運訂艙
        sea_bookings = [r for r in history if r.get("best_mode") == "海運"]
        
        total_bookings = len(sea_bookings)
        total_containers = sum(r.get("containers", 0) for r in sea_bookings)
        total_revenue = sum(r.get("sea_total", 0) for r in sea_bookings)
        avg_booking_size = round(total_containers / total_bookings) if total_bookings > 0 else 0
        
        return jsonify({
            "total_bookings": total_bookings,
            "total_containers": total_containers,
            "total_revenue": total_revenue,
            "avg_booking_size": avg_booking_size
        })
    except Exception as e:
        print(f"訂艙統計錯誤: {e}")
        return jsonify({
            "total_bookings": 0,
            "total_containers": 0,
            "total_revenue": 0,
            "avg_booking_size": 0
        })

@app.route("/api/bookings")
def get_bookings():
    """取得訂票記錄"""
    company = request.args.get("company")
    history = load_history()
    
    # 只篩選海運記錄
    bookings = [r for r in history if r.get("best_mode") == "海運"]
    
    if company:
        bookings = [b for b in bookings if b.get("company_name", "").lower() == company.lower()]
    
    # 按日期排序（最新的在前）
    bookings.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    result = []
    for b in bookings[:50]:
        result.append({
            "booking_id": b.get("id", b.get("booking_id", "")),
            "company_name": b.get("company_name", b.get("start", "")),
            "route": f"{b.get('start', '')} → {b.get('end', '')}",
            "containers": b.get("containers", 0),
            "sailing_date": b.get("ship_date", b.get("date", "").split(" ")[0]),
            "total_price": b.get("sea_total", 0),
            "status": "confirmed",
            "booking_date": b.get("date", "")
        })
    
    return jsonify(result)

@app.route("/api/book-ship", methods=["POST"])
def book_ship():
    """預訂船班艙位 - 直接儲存到歷史記錄"""
    try:
        data = request.get_json()
        print(f"收到訂艙請求: {data}")
        
        route_key = data.get("route_key")
        sailing_date = data.get("sailing_date")
        containers = data.get("containers", 1)
        company_name = data.get("company_name", "")
        cargo_type = data.get("cargo_type", "normal")
        contact_person = data.get("contact_person", "")
        phone = data.get("phone", "")
        
        # 產生訂艙編號
        booking_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
        
        # 計算價格
        container_type = data.get("container_type", "40ft")
        if container_type == "20ft":
            price_per_container = 1800
        else:
            price_per_container = 2787
        
        total_price = price_per_container * containers
        
        # 儲存到歷史記錄
        history_record = {
            "id": booking_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "booking_id": booking_id,
            "company_name": company_name,
            "contact_person": contact_person,
            "phone": phone,
            "start": data.get("start_name", "高雄港"),
            "end": data.get("end_name", "台中港"),
            "containers": containers,
            "container_type": container_type,
            "cargo_type": cargo_type,
            "best_mode": "海運",
            "ship_date": sailing_date,
            "sea_total": total_price,
            "carbon_improvement": 0,
            "savings_amount": 0,
            "status": "confirmed"
        }
        
        history = load_history()
        history.append(history_record)
        
        if len(history) > MAX_HISTORY_RECORDS:
            history = history[-MAX_HISTORY_RECORDS:]
        
        write_json(HISTORY_FILE, history)
        
        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "total_price": total_price,
            "ship_name": "UNI-PROSPER",
            "sailing_date": sailing_date,
            "containers": containers,
            "message": "訂艙成功"
        })
        
    except Exception as e:
        print(f"訂艙錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

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
        
        # 確保明細欄位存在
        optional_fields = [
            "departure_date", "arrival_requirement", "sea_arrival_date", 
            "road_arrival_date", "voyage_no", "ship_date", "company_name",
            "contact_person", "phone", "sea_carbon_fee", "sea_carbon_credit",
            "road_carbon_fee", "road_carbon_credit", "base_distance",
            "road_carbon", "sea_carbon", "road_total", "sea_total", "container_type"
        ]
        for field in optional_fields:
            if field not in data:
                data[field] = None
        
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

    # 計算碳排 - 使用修正後的公式
    ROAD_CARBON_RATE_PER_KM = 2.925
    SEA_CARBON_RATE_PER_KM = 0.675
    
    road_carbon = ROAD_CARBON_RATE_PER_KM * road_distance * containers
    sea_carbon = SEA_CARBON_RATE_PER_KM * sea_distance * containers + PORT_HANDLING_EMISSION_PER_CONTAINER * containers * 2

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

# ================= 日期區間證書產生 API =================
@app.route("/api/generate_certificate", methods=["POST"])
def api_generate_certificate():
    """根據日期區間產生減碳證書 PDF"""
    try:
        data = request.get_json()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        company_name = data.get("company_name", "iMarine Customer")
        
        if not start_date or not end_date:
            return jsonify({"error": "請提供開始和結束日期"}), 400
        
        history = load_history()
        
        # 篩選日期區間的記錄
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        end = end.replace(hour=23, minute=59, second=59)
        
        filtered_records = []
        for record in history:
            try:
                record_date_str = record.get("date", "").split(" ")[0]
                if record_date_str:
                    record_date = datetime.strptime(record_date_str, "%Y-%m-%d")
                    if start <= record_date <= end:
                        filtered_records.append(record)
            except:
                continue
        
        # 計算統計數據
        total_containers = sum(r.get("containers", 0) for r in filtered_records)
        total_carbon_saved = sum(r.get("carbon_improvement", 0) for r in filtered_records)
        total_cost_saved = sum(r.get("savings_amount", 0) for r in filtered_records)
        sea_count = len([r for r in filtered_records if r.get("best_mode") == "海運"])
        road_count = len([r for r in filtered_records if r.get("best_mode") == "內陸運輸" or r.get("best_mode") == "公路"])
        
        # 產生證書 PDF
        pdf_buffer = build_certificate_pdf_report(
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            total_containers=total_containers,
            total_carbon_saved=total_carbon_saved,
            total_cost_saved=total_cost_saved,
            sea_count=sea_count,
            road_count=road_count,
            records=filtered_records[:20]
        )
        
        return send_file(
            pdf_buffer, 
            as_attachment=True, 
            download_name=f"carbon_certificate_{start_date}_to_{end_date}.pdf",
            mimetype="application/pdf"
        )
        
    except Exception as e:
        print(f"產生證書錯誤: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)