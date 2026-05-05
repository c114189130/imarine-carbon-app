import os
import math
import requests
from datetime import datetime
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

from config import *
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.schedule_service import ScheduleService
from services.storage_service import ensure_json_file, read_json, write_json

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

REQUEST_TIMEOUT = 8
schedule_service = ScheduleService()

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def get_tdx_token():
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET:
        return None
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    try:
        res = requests.post(url, data={"grant_type":"client_credentials","client_id":TDX_CLIENT_ID,"client_secret":TDX_CLIENT_SECRET}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return res.json()["access_token"]
    except:
        pass
    return None


def get_tdx_highway_traffic():
    """取得國道即時路況"""
    token = get_tdx_token()
    if not token:
        return {"avg_speed": 55, "nh1_speed": 58, "nh3_speed": 52, "congestion": "medium"}
    try:
        res = requests.get(
            "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON",
            headers={"authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT
        )
        if res.status_code == 200:
            data = res.json()
            nh1_speeds, nh3_speeds = [], []
            for item in data.get("Data", []):
                if "Speed" not in item: continue
                vd = item.get("VDID", "")
                if "NH1" in vd or "N1" in vd: nh1_speeds.append(item["Speed"])
                elif "NH3" in vd or "N3" in vd: nh3_speeds.append(item["Speed"])
                else: nh1_speeds.append(item["Speed"])
            n1 = round(sum(nh1_speeds)/len(nh1_speeds),1) if nh1_speeds else 50
            n3 = round(sum(nh3_speeds)/len(nh3_speeds),1) if nh3_speeds else 50
            avg = round((sum(nh1_speeds)+sum(nh3_speeds))/(len(nh1_speeds)+len(nh3_speeds)),1) if (nh1_speeds or nh3_speeds) else 50
            cong = "low" if avg >= 60 else ("medium" if avg >= 35 else "high")
            return {"avg_speed": avg, "nh1_speed": n1, "nh3_speed": n3, "congestion": cong}
    except:
        pass
    return {"avg_speed": 55, "nh1_speed": 58, "nh3_speed": 52, "congestion": "medium"}


def build_calculation_result(start, end, containers, container_unit="FEU", ship_date=""):
    """核心計算函數"""
    # TEU/FEU 換算
    if container_unit == "TEU":
        containers_feu = float(containers) * TEU_TO_FEU_RATIO
        container_display = f"{containers} TEU（約 {containers_feu:.1f} FEU）"
    else:
        containers_feu = float(containers)
        container_display = f"{containers} FEU"
    
    p1 = PORTS[start]
    p2 = PORTS[end]
    
    # 取得路線距離
    route_key = (start, end)
    route_info = ROUTES_INFO.get(route_key, {})
    road_km = route_info.get("road_km", round(haversine_distance(p1["lat"],p1["lon"],p2["lat"],p2["lon"])*1.22))
    sea_km = route_info.get("sea_km", round(haversine_distance(p1["lat"],p1["lon"],p2["lat"],p2["lon"])*1.08))
    
    # 公路路況
    traffic = get_tdx_highway_traffic()
    # 根據壅塞程度調整公路時間
    congestion_factor = {"low": 1.0, "medium": 1.2, "high": 1.5}
    road_time_hours = round(road_km / ROAD_SPEED_KMH * congestion_factor.get(traffic["congestion"], 1.0), 1)
    
    # 船班查詢（附多個航次）
    ship_schedules = schedule_service.get_ship_schedules(p1["code"], p2["name"], containers_feu, ship_date)
    
    # 碳排放計算
    road_carbon = EMISSION_FACTORS["road"] * road_km * containers_feu
    sea_carbon = EMISSION_FACTORS["sea"] * sea_km * containers_feu + PORT_HANDLING_EMISSION * containers_feu * 2
    
    # 作業費計算
    road_freight = TRANSPORT_COST_RATES["road"] * road_km * containers_feu
    sea_freight = TRANSPORT_COST_RATES["sea"] * sea_km * containers_feu
    
    # 運輸成本（含裝卸）
    road_total = road_freight
    sea_total = sea_freight
    
    # 海運節省
    cost_savings = road_total - sea_total  # 正數表示海運較便宜
    
    # 碳排改善
    carbon_improvement = road_carbon - sea_carbon
    reduction_pct = round(carbon_improvement / road_carbon * 100, 1) if road_carbon > 0 else 0
    
    # 碳權價值
    carbon_credit_value = round(carbon_improvement * CARBON_PRICE_PER_KG, 2)
    
    # 最佳模式判斷
    if cost_savings > 0:
        best_mode = "海轉（藍色公路）"
    else:
        best_mode = "陸拖（公路運輸）"
    
    # 儲存記錄
    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"], "end": p2["name"],
        "containers": containers, "container_unit": container_unit, "containers_feu": round(containers_feu,1),
        "ship_date": ship_date,
        "road_km": road_km, "sea_km": sea_km,
        "road_carbon": round(road_carbon,2), "sea_carbon": round(sea_carbon,2),
        "carbon_improvement": round(carbon_improvement,2), "reduction_pct": reduction_pct,
        "carbon_credit_value": carbon_credit_value,
        "best_mode": best_mode, "cost_savings": round(cost_savings),
        "road_total": round(road_total), "sea_total": round(sea_total),
    }
    save_history(record)
    
    return {
        "record_id": record["id"],
        "start_name": p1["name"], "end_name": p2["name"],
        "start_lat": p1["lat"], "start_lon": p1["lon"],
        "end_lat": p2["lat"], "end_lon": p2["lon"],
        "containers": containers, "container_unit": container_unit,
        "containers_feu": round(containers_feu,1), "container_display": container_display,
        "ship_date": ship_date,
        "road_km": road_km, "sea_km": sea_km,
        "road_time_hours": road_time_hours,
        "road": {
            "freight": round(road_freight),
            "carbon": round(road_carbon,2),
            "total": round(road_total),
            "time_hours": road_time_hours
        },
        "sea": {
            "freight": round(sea_freight),
            "carbon": round(sea_carbon,2),
            "total": round(sea_total),
        },
        "best_mode": best_mode,
        "cost_savings": round(cost_savings),
        "carbon_improvement": round(carbon_improvement,2),
        "reduction_pct": reduction_pct,
        "carbon_credit_value": carbon_credit_value,
        "traffic": {
            "avg_speed": traffic["avg_speed"],
            "nh1_speed": traffic["nh1_speed"],
            "nh3_speed": traffic["nh3_speed"],
            "congestion": traffic["congestion"],
            "congestion_text": "順暢" if traffic["congestion"]=="low" else ("車多" if traffic["congestion"]=="medium" else "壅塞")
        },
        "ship_schedules": ship_schedules,
    }


def load_history():
    return read_json(HISTORY_FILE, [])

def save_history(record):
    h = load_history()
    h.append(record)
    write_json(HISTORY_FILE, h[-MAX_HISTORY_RECORDS:])

def load_certificates():
    return read_json(CERTIFICATE_FILE, [])

def save_certificate(cert):
    rows = load_certificates()
    rows.append(cert)
    write_json(CERTIFICATE_FILE, rows)

def get_history_record(rid):
    for r in load_history():
        if r["id"] == rid: return r
    return None

def get_certificate(cid):
    for c in load_certificates():
        if c["cert_id"] == cid: return c
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
    segments = ["NH1-N-0","NH1-S-1","NH1-S-2","NH1-S-3","NH1-S-4",
                "NH3-N-0","NH3-S-1","NH3-S-2","NH3-S-3","NH3-S-4","NH3-S-5","NH5-S-0"]
    token = get_tdx_token()
    if not token:
        return jsonify([{"id":s,"speed":55} for s in segments])
    try:
        res = requests.get(
            "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON",
            headers={"authorization":f"Bearer {token}"}, timeout=REQUEST_TIMEOUT
        )
        if res.status_code == 200:
            speeds = [i["Speed"] for i in res.json().get("Data",[]) if "Speed" in i]
            if speeds:
                return jsonify([{"id":segments[i%len(segments)],"speed":speeds[i%len(speeds)]} for i in range(len(segments))])
    except: pass
    return jsonify([{"id":s,"speed":55} for s in segments])

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")
    containers = data.get("containers")
    container_unit = data.get("container_unit", "FEU")
    ship_date = data.get("ship_date", "")
    
    if start not in PORTS or end not in PORTS:
        return jsonify({"error": "港口代碼無效"}), 400
    if start == end:
        return jsonify({"error": "起點與終點不可相同"}), 400
    try:
        containers = int(containers)
    except:
        return jsonify({"error": "貨櫃數量格式錯誤"}), 400
    if containers <= 0 or containers > 5000:
        return jsonify({"error": "貨櫃數量需介於 1 到 5000 之間"}), 400
    
    try:
        return jsonify(build_calculation_result(start, end, containers, container_unit, ship_date))
    except Exception as e:
        return jsonify({"error": f"計算失敗: {str(e)}"}), 500

@app.route("/certificate", methods=["POST"])
def create_certificate():
    data = request.get_json(silent=True) or {}
    record_id = data.get("record_id")
    company_name = (data.get("company_name") or "").strip()
    if not company_name: return jsonify({"error":"請輸入公司名稱"}), 400
    if not record_id: return jsonify({"error":"缺少計算紀錄 ID"}), 400
    record = get_history_record(record_id)
    if not record: return jsonify({"error":"查無對應的計算紀錄"}), 404
    cert_id = generate_certificate_id()
    cert = {"cert_id":cert_id,"company_name":company_name,"issued_at":datetime.now().strftime("%Y-%m-%d"),"record_id":record_id,"record":record}
    save_certificate(cert)
    return jsonify({"cert_id":cert_id,"company_name":company_name,"issued_at":cert["issued_at"],
                    "route":f"{record['start']} → {record['end']}","containers":record["containers"],
                    "carbon_improvement":record["carbon_improvement"],"reduction_pct":record["reduction_pct"]})

@app.route("/download_certificate/<cert_id>/<lang>")
def download_certificate(cert_id, lang):
    cert = get_certificate(cert_id)
    if not cert: return jsonify({"error":"查無證書"}), 404
    lang = "en" if lang=="en" else "zh"
    buf = build_certificate_pdf(cert, lang=lang)
    return send_file(buf, as_attachment=True, download_name=f"certificate_{cert_id}.pdf", mimetype="application/pdf")

@app.route("/verify/<cert_id>")
def verify_certificate(cert_id):
    cert = get_certificate(cert_id)
    return render_template("verify.html", valid=bool(cert), cert=cert, app_title=APP_TITLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)