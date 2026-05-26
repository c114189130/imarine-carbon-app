import os
import math
import requests
import random
from datetime import datetime, timedelta
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
)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# ================= 輔助函數 =================
def ensure_json_file(file_path, default_content):
    """確保 JSON 檔案存在"""
    import json
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_content, f, ensure_ascii=False, indent=2)

def read_json(file_path):
    """讀取 JSON 檔案"""
    import json
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file_path, data):
    """寫入 JSON 檔案"""
    import json
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

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

# 初始化檔案
ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])

# ================= 模擬船期資料 =================
REAL_SCHEDULE = [
    {"voyage": "0727-511B", "kaohsiung_depart": "2026-05-07", "taichung_arrive": "2026-05-08", "taipei_arrive": "2026-05-12"},
    {"voyage": "0728-512B", "kaohsiung_depart": "2026-05-13", "taichung_arrive": "2026-05-16", "taipei_arrive": "2026-05-19"},
    {"voyage": "0729-513B", "kaohsiung_depart": "2026-05-20", "taichung_arrive": "2026-05-23", "taipei_arrive": "2026-05-26"},
    {"voyage": "0730-514B", "kaohsiung_depart": "2026-05-27", "taichung_arrive": "2026-05-30", "taipei_arrive": "2026-06-01"},
    {"voyage": "0731-515B", "kaohsiung_depart": "2026-06-03", "taichung_arrive": "2026-06-06", "taipei_arrive": "2026-06-09"},
    {"voyage": "0732-516B", "kaohsiung_depart": "2026-06-10", "taichung_arrive": "2026-06-13", "taipei_arrive": "2026-06-16"},
    {"voyage": "0733-517B", "kaohsiung_depart": "2026-06-17", "taichung_arrive": "2026-06-21", "taipei_arrive": "2026-06-23"},
    {"voyage": "0734-518B", "kaohsiung_depart": "2026-06-25", "taichung_arrive": "2026-06-28", "taipei_arrive": "2026-06-30"},
]

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
    """取得即時路況 - 模擬資料"""
    try:
        current_hour = datetime.now().hour
        
        # 根據時間模擬不同路況
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            speeds = [random.randint(30, 50) for _ in range(5)]
        elif 11 <= current_hour <= 13:
            speeds = [random.randint(50, 70) for _ in range(5)]
        else:
            speeds = [random.randint(60, 90) for _ in range(5)]
        
        return jsonify([
            {"road": f"國道{num}號", "speed": speeds[i]}
            for i, num in enumerate([1, 3, 5, 10, 18])
        ])
    except Exception as e:
        print(f"路況 API 錯誤: {e}")
        return jsonify([
            {"road": "國道1號", "speed": 65},
            {"road": "國道3號", "speed": 70},
            {"road": "國道5號", "speed": 60},
            {"road": "國道10號", "speed": 75},
            {"road": "國道18號", "speed": 68},
        ])

@app.route("/api/ships/<route_key>")
def get_ships(route_key):
    """取得航線所有船班艙位資訊 - 模擬資料"""
    try:
        ships = []
        today = datetime.now()
        
        for i, schedule in enumerate(REAL_SCHEDULE):
            sailing_date_str = schedule["kaohsiung_depart"]
            sailing_date = datetime.strptime(sailing_date_str, "%Y-%m-%d")
            
            # 只顯示未來的船班
            if sailing_date >= today:
                utilization = random.randint(20, 90)
                remaining = int(500 * (1 - utilization / 100))
                
                ships.append({
                    "ship_name": "UNI-PROSPER",
                    "voyage_no": schedule["voyage"],
                    "sailing_date": sailing_date_str,
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
    """取得訂票摘要統計"""
    try:
        history = load_history()
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
    bookings = [r for r in history if r.get("best_mode") == "海運"]
    
    if company:
        bookings = [b for b in bookings if b.get("company_name", "").lower() == company.lower()]
    
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
    """預訂船班艙位"""
    try:
        data = request.get_json()
        print(f"收到訂艙請求: {data}")
        
        sailing_date = data.get("sailing_date")
        containers = data.get("containers", 1)
        company_name = data.get("company_name", "")
        cargo_type = data.get("cargo_type", "normal")
        contact_person = data.get("contact_person", "")
        phone = data.get("phone", "")
        container_type = data.get("container_type", "40ft")
        start_name = data.get("start_name", "高雄港")
        end_name = data.get("end_name", "台中港")
        
        booking_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
        
        # 價格
        if container_type == "20ft":
            price_per_container = 1800
        else:
            price_per_container = 2787
        
        total_price = price_per_container * containers
        
        history_record = {
            "id": booking_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "booking_id": booking_id,
            "company_name": company_name,
            "contact_person": contact_person,
            "phone": phone,
            "start": start_name,
            "end": end_name,
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
    """直接保存歷史記錄"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "無資料"}), 400
        
        if "id" not in data:
            data["id"] = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
        if "date" not in data:
            data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if "savings_amount" not in data or data.get("savings_amount") is None:
            carbon_improvement = data.get("carbon_improvement", 0)
            data["savings_amount"] = round(carbon_improvement * 0.3)
        
        history = load_history()
        history.append(data)
        
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

    p1 = PORTS[start]
    p2 = PORTS[end]
    base_distance = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
    
    # 模擬路況
    current_hour = datetime.now().hour
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        road_speed = 45
        road_level = "medium"
        road_level_text = "🟡 車多"
    elif 11 <= current_hour <= 13:
        road_speed = 60
        road_level = "low"
        road_level_text = "🟢 順暢"
    else:
        road_speed = 75
        road_level = "low"
        road_level_text = "🟢 順暢"
    
    road_condition = {
        "level": road_level,
        "level_text": road_level_text,
        "avg_speed": road_speed
    }
    
    # 模擬船期
    ship_schedule = []
    today = datetime.now()
    for schedule in REAL_SCHEDULE[:3]:
        sailing_date = datetime.strptime(schedule["kaohsiung_depart"], "%Y-%m-%d")
        if sailing_date >= today:
            ship_schedule.append({
                "voyage": schedule["voyage"],
                "departure": schedule["kaohsiung_depart"],
                "arrival": schedule["taipei_arrive"] if end == "taipei" else schedule["taichung_arrive"]
            })
    
    # 碳排計算
    ROAD_CARBON_RATE = 2.925
    SEA_CARBON_RATE = 0.675
    
    road_carbon = ROAD_CARBON_RATE * base_distance * containers
    sea_carbon = SEA_CARBON_RATE * base_distance * containers
    
    road_cost = 7218 * containers
    sea_cost = 2787 * containers
    
    if sea_cost < road_cost:
        best_mode = "海運"
        carbon_improvement = road_carbon - sea_carbon
        savings_amount = road_cost - sea_cost
    else:
        best_mode = "公路"
        carbon_improvement = sea_carbon - road_carbon
        savings_amount = 0
    
    reduction_pct = (carbon_improvement / road_carbon * 100) if road_carbon > 0 else 0
    
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
        "savings_amount": round(savings_amount),
        "road_total": round(road_cost),
        "sea_total": round(sea_cost),
    }
    save_history(record)
    
    return jsonify({
        "record_id": record["id"],
        "distance": round(base_distance, 2),
        "containers": containers,
        "start_name": p1["name"],
        "end_name": p2["name"],
        "road": {
            "freight": round(road_cost),
            "carbon": round(road_carbon, 2),
            "total": round(road_cost),
        },
        "sea": {
            "freight": round(sea_cost),
            "carbon": round(sea_carbon, 2),
            "total": round(sea_cost),
        },
        "best_mode": best_mode,
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "recommendation": f"選擇 {best_mode} 可減少 {carbon_improvement:.0f} kg CO2e",
        "road_condition": road_condition,
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

    cert_id = f"IMC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
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
    return jsonify({"message": "證書下載功能開發中", "cert_id": cert_id})

@app.route("/api/generate_certificate", methods=["POST"])
def api_generate_certificate():
    try:
        data = request.get_json()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        company_name = data.get("company_name", "iMarine Customer")
        
        if not start_date or not end_date:
            return jsonify({"error": "請提供開始和結束日期"}), 400
        
        history = load_history()
        
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
        
        total_containers = sum(r.get("containers", 0) for r in filtered_records)
        total_carbon_saved = sum(r.get("carbon_improvement", 0) for r in filtered_records)
        total_cost_saved = sum(r.get("savings_amount", 0) for r in filtered_records)
        sea_count = len([r for r in filtered_records if r.get("best_mode") == "海運"])
        road_count = len([r for r in filtered_records if r.get("best_mode") == "公路" or r.get("best_mode") == "內陸運輸"])
        
        # 產生簡單的 PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph(f"Carbon Reduction Certificate", styles['Title']))
        content.append(Spacer(1, 12))
        content.append(Paragraph(f"Company: {company_name}", styles['Normal']))
        content.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        content.append(Spacer(1, 12))
        content.append(Paragraph(f"Total Containers: {total_containers}", styles['Normal']))
        content.append(Paragraph(f"Total CO₂ Saved: {total_carbon_saved:,.0f} kg", styles['Normal']))
        content.append(Paragraph(f"Total Cost Saved: NT$ {total_cost_saved:,.0f}", styles['Normal']))
        content.append(Paragraph(f"Sea Shipments: {sea_count}", styles['Normal']))
        content.append(Paragraph(f"Road Shipments: {road_count}", styles['Normal']))
        content.append(Spacer(1, 20))
        content.append(Paragraph("iMarine Carbon Management Platform", styles['Normal']))
        
        doc.build(content)
        buffer.seek(0)
        
        return send_file(
            buffer, 
            as_attachment=True, 
            download_name=f"carbon_certificate_{start_date}_to_{end_date}.pdf",
            mimetype="application/pdf"
        )
        
    except Exception as e:
        print(f"產生證書錯誤: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)