import os
import math
import requests
from datetime import datetime
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

from config import (
    APP_TITLE,
    CERTIFICATE_FILE,
    HISTORY_FILE,
    MAX_HISTORY_RECORDS,
    PORTS,
    PORT_HANDLING_EMISSION_PER_CONTAINER,
    ROAD_SPEED_KMH,
    SEA_SPEED_KMH,
    SECRET_KEY,
    TRANSPORT_COST_RATES,
    EMISSION_FACTORS,
    TDX_CLIENT_ID,
    TDX_CLIENT_SECRET,
)
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.schedule_service import ScheduleService
from services.storage_service import ensure_json_file, read_json, write_json

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# 設定全域請求 timeout（秒）
REQUEST_TIMEOUT = 8

schedule_service = ScheduleService()

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])


# ================= TDX API =================
def get_tdx_token():
    """取得 TDX API Token，若無憑證或失敗則回傳 None"""
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET:
        print("⚠️ TDX 憑證未設定，使用模擬路況資料")
        return None

    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": TDX_CLIENT_ID,
        "client_secret": TDX_CLIENT_SECRET
    }
    try:
        res = requests.post(url, data=data, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return res.json()["access_token"]
        else:
            print(f"TDX Token 失敗: HTTP {res.status_code}")
    except requests.exceptions.Timeout:
        print("❌ TDX Token 請求超時")
    except Exception as e:
        print(f"TDX Token 錯誤: {e}")
    return None


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def estimate_route_distance(base_distance_km, mode):
    multiplier = 1.22 if mode == "road" else 1.08
    return round(base_distance_km * multiplier, 2)


def get_road_condition():
    """取得國道即時路況（若 TDX 不可用則回傳模擬資料，不阻擋計算）"""
    token = get_tdx_token()
    
    # 無 Token 時直接回傳模擬資料
    if not token:
        return {
            "level": "medium",
            "avg_speed": 55,
            "nh1_speed": 58,
            "nh3_speed": 52,
            "is_simulated": True
        }
    
    url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON"
    headers = {"authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            nh1_speeds = []
            nh3_speeds = []
            
            for item in data.get("Data", []):
                if "Speed" not in item:
                    continue
                vd_id = item.get("VDID", "")
                if "NH1" in vd_id or "N1" in vd_id:
                    nh1_speeds.append(item["Speed"])
                elif "NH3" in vd_id or "N3" in vd_id:
                    nh3_speeds.append(item["Speed"])
                else:
                    nh1_speeds.append(item["Speed"])
            
            nh1_avg = round(sum(nh1_speeds) / len(nh1_speeds), 1) if nh1_speeds else 50
            nh3_avg = round(sum(nh3_speeds) / len(nh3_speeds), 1) if nh3_speeds else 50
            
            all_speeds = nh1_speeds + nh3_speeds
            avg_speed = round(sum(all_speeds) / len(all_speeds), 1) if all_speeds else 50
            
            if avg_speed >= 60:
                level = "low"
            elif avg_speed >= 35:
                level = "medium"
            else:
                level = "high"
            
            return {
                "level": level,
                "avg_speed": avg_speed,
                "nh1_speed": nh1_avg,
                "nh3_speed": nh3_avg,
                "is_simulated": False
            }
    except requests.exceptions.Timeout:
        print("❌ TDX 路況請求超時，使用模擬資料")
    except Exception as e:
        print(f"TDX API 錯誤: {e}")
    
    return {
        "level": "medium",
        "avg_speed": 55,
        "nh1_speed": 58,
        "nh3_speed": 52,
        "is_simulated": True
    }


def build_calculation_result(start, end, containers, ship_date=""):
    """建立計算結果（只計算作業費，FEU）"""
    containers_feu = float(containers)
    
    p1 = PORTS[start]
    p2 = PORTS[end]
    base_distance = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
    road_distance = estimate_route_distance(base_distance, "road")
    sea_distance = estimate_route_distance(base_distance, "sea")

    # 路況資訊（即使 TDX 失敗也會有模擬資料）
    road_condition = get_road_condition()
    
    # 船班資訊（從靜態 JSON 讀取，永遠不會失敗）
    ship_schedule = schedule_service.get_ship_schedule(p1["code"], p2["name"], ship_date)

    # 碳排放計算
    road_carbon = EMISSION_FACTORS["road"] * road_distance * containers_feu
    sea_carbon = EMISSION_FACTORS["sea"] * sea_distance * containers_feu + PORT_HANDLING_EMISSION_PER_CONTAINER * containers_feu * 2

    # 作業費計算
    road_freight = TRANSPORT_COST_RATES["road"] * road_distance * containers_feu
    sea_freight = TRANSPORT_COST_RATES["sea"] * sea_distance * containers_feu

    # 總成本 = 作業費
    road_total = road_freight
    sea_total = sea_freight

    # 判斷最佳模式
    if sea_total < road_total:
        best_mode = "海運"
        cost_savings = road_total - sea_total
    else:
        best_mode = "公路"
        cost_savings = sea_total - road_total

    # 碳排改善
    carbon_improvement = road_carbon - sea_carbon
    reduction_pct = (carbon_improvement / road_carbon * 100) if road_carbon > 0 else 0

    # 儲存歷史記錄
    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"],
        "end": p2["name"],
        "containers": containers,
        "ship_date": ship_date,
        "base_distance": round(base_distance, 2),
        "road_distance": round(road_distance, 2),
        "sea_distance": round(sea_distance, 2),
        "road_carbon": round(road_carbon, 2),
        "sea_carbon": round(sea_carbon, 2),
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "best_mode": best_mode,
        "cost_savings": round(cost_savings),
        "road_total": round(road_total),
        "sea_total": round(sea_total),
    }
    save_history(record)

    return {
        "record_id": record["id"],
        "distance": round(base_distance, 2),
        "road_distance": round(road_distance, 2),
        "sea_distance": round(sea_distance, 2),
        "containers": containers,
        "ship_date": ship_date,
        "start_name": p1["name"],
        "end_name": p2["name"],
        "start_lat": p1["lat"],
        "start_lon": p1["lon"],
        "end_lat": p2["lat"],
        "end_lon": p2["lon"],
        "road": {
            "freight": round(road_freight),
            "carbon": round(road_carbon, 2),
            "total": round(road_total),
        },
        "sea": {
            "freight": round(sea_freight),
            "carbon": round(sea_carbon, 2),
            "total": round(sea_total),
        },
        "best_mode": best_mode,
        "cost_savings": round(cost_savings),
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "recommendation": f"選擇 {best_mode} 相較替代方案可節省 NT$ {cost_savings:,} 作業費",
        "carbon_savings_text": f"🚢 海運相較公路可減少 {carbon_improvement:.0f} kg CO2e（約 {reduction_pct:.1f}%）",
        "road_condition": {
            "level": road_condition["level"],
            "level_text": "🟢 順暢" if road_condition["level"] == "low" else "🟡 車多" if road_condition["level"] == "medium" else "🔴 壅塞",
            "avg_speed": road_condition["avg_speed"],
            "nh1_speed": road_condition.get("nh1_speed", 50),
            "nh3_speed": road_condition.get("nh3_speed", 50),
            "is_simulated": road_condition.get("is_simulated", True),
        },
        "ship_schedule": ship_schedule,
    }


# ================= 資料存取 =================
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

@app.route("/input")
def input_page():
    return render_template("input.html", ports=PORTS, app_title=APP_TITLE)

@app.route("/result")
def result_page():
    return render_template("result.html", app_title=APP_TITLE)

@app.route("/certificate_page")
def certificate_page():
    return render_template("certificate.html", app_title=APP_TITLE)

@app.route("/history_page")
def history_page():
    return render_template("history.html", app_title=APP_TITLE)

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", app_title=APP_TITLE)

@app.route("/get_history")
def get_history():
    return jsonify(load_history())

@app.route("/api/traffic")
def api_traffic():
    """國道路段即時時速（若 TDX 失敗回傳模擬資料）"""
    token = get_tdx_token()
    
    if not token:
        return jsonify([
            {"id": "NH1-N-0", "speed": 55}, {"id": "NH1-S-1", "speed": 48},
            {"id": "NH1-S-2", "speed": 62}, {"id": "NH1-S-3", "speed": 40},
            {"id": "NH1-S-4", "speed": 70}, {"id": "NH3-N-0", "speed": 58},
            {"id": "NH3-S-1", "speed": 65}, {"id": "NH3-S-2", "speed": 35},
            {"id": "NH3-S-3", "speed": 52}, {"id": "NH3-S-4", "speed": 68},
            {"id": "NH3-S-5", "speed": 45}, {"id": "NH5-S-0", "speed": 60},
        ])
    
    url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON"
    headers = {"authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            road_segments = [
                "NH1-N-0", "NH1-S-1", "NH1-S-2", "NH1-S-3", "NH1-S-4",
                "NH3-N-0", "NH3-S-1", "NH3-S-2", "NH3-S-3", "NH3-S-4", "NH3-S-5",
                "NH5-S-0"
            ]
            results = []
            speeds = [item["Speed"] for item in data.get("Data", []) if "Speed" in item]
            
            if speeds:
                for i, seg in enumerate(road_segments):
                    idx = i % len(speeds)
                    results.append({"id": seg, "speed": speeds[idx]})
            
            if not results:
                for seg in road_segments:
                    results.append({"id": seg, "speed": 60})
            
            return jsonify(results)
    except requests.exceptions.Timeout:
        print("❌ /api/traffic 請求超時")
    except Exception as e:
        print(f"TDX API 錯誤: {e}")
    
    return jsonify([
        {"id": "NH1-N-0", "speed": 55}, {"id": "NH1-S-1", "speed": 48},
        {"id": "NH1-S-2", "speed": 62}, {"id": "NH1-S-3", "speed": 40},
        {"id": "NH1-S-4", "speed": 70}, {"id": "NH3-N-0", "speed": 58},
        {"id": "NH3-S-1", "speed": 65}, {"id": "NH3-S-2", "speed": 35},
        {"id": "NH3-S-3", "speed": 52}, {"id": "NH3-S-4", "speed": 68},
        {"id": "NH3-S-5", "speed": 45}, {"id": "NH5-S-0", "speed": 60},
    ])


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")
    containers = data.get("containers")
    ship_date = data.get("ship_date", "")

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

    try:
        result = build_calculation_result(start, end, containers, ship_date)
        return jsonify(result)
    except Exception as e:
        print(f"❌ 計算錯誤: {e}")
        return jsonify({"error": f"計算失敗: {str(e)}"}), 500


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


@app.route("/verify/<cert_id>")
def verify_certificate(cert_id):
    certificate = get_certificate(cert_id)
    return render_template("verify.html", valid=bool(certificate), cert=certificate, app_title=APP_TITLE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)