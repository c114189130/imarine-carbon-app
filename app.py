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


def get_tdx_token():
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET:
        return None
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    try:
        res = requests.post(url, data={"grant_type": "client_credentials", "client_id": TDX_CLIENT_ID, "client_secret": TDX_CLIENT_SECRET}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return res.json()["access_token"]
    except:
        pass
    return None


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def estimate_route_distance(base, mode):
    return round(base * (1.22 if mode == "road" else 1.08), 2)


def get_road_condition():
    token = get_tdx_token()
    if not token:
        return {"level": "medium", "avg_speed": 55, "nh1_speed": 58, "nh3_speed": 52}
    try:
        res = requests.get("https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON", headers={"authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            nh1, nh3 = [], []
            for item in data.get("Data", []):
                if "Speed" not in item: continue
                vd = item.get("VDID", "")
                if "NH1" in vd or "N1" in vd: nh1.append(item["Speed"])
                elif "NH3" in vd or "N3" in vd: nh3.append(item["Speed"])
                else: nh1.append(item["Speed"])
            n1avg = round(sum(nh1)/len(nh1),1) if nh1 else 50
            n3avg = round(sum(nh3)/len(nh3),1) if nh3 else 50
            allsp = nh1 + nh3
            avg = round(sum(allsp)/len(allsp),1) if allsp else 50
            level = "low" if avg >= 60 else ("medium" if avg >= 35 else "high")
            return {"level": level, "avg_speed": avg, "nh1_speed": n1avg, "nh3_speed": n3avg}
    except:
        pass
    return {"level": "medium", "avg_speed": 55, "nh1_speed": 58, "nh3_speed": 52}


def build_calculation_result(start, end, containers, ship_date=""):
    cf = float(containers)
    p1, p2 = PORTS[start], PORTS[end]
    base = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
    rd = estimate_route_distance(base, "road")
    sd = estimate_route_distance(base, "sea")

    rc = get_road_condition()
    ss = schedule_service.get_ship_schedule(p1["code"], p2["name"], ship_date)

    road_carbon = EMISSION_FACTORS["road"] * rd * cf
    sea_carbon = EMISSION_FACTORS["sea"] * sd * cf + PORT_HANDLING_EMISSION_PER_CONTAINER * cf * 2

    road_freight = TRANSPORT_COST_RATES["road"] * rd * cf
    sea_freight = TRANSPORT_COST_RATES["sea"] * sd * cf

    road_total = road_freight
    sea_total = sea_freight

    if sea_total < road_total:
        best_mode = "海運"
        cost_savings = road_total - sea_total
    else:
        best_mode = "公路"
        cost_savings = sea_total - road_total

    carbon_improvement = road_carbon - sea_carbon
    reduction_pct = (carbon_improvement / road_carbon * 100) if road_carbon > 0 else 0

    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"], "end": p2["name"],
        "containers": containers, "ship_date": ship_date,
        "base_distance": round(base,2), "road_distance": rd, "sea_distance": sd,
        "road_carbon": round(road_carbon,2), "sea_carbon": round(sea_carbon,2),
        "carbon_improvement": round(carbon_improvement,2), "reduction_pct": round(reduction_pct,1),
        "best_mode": best_mode, "cost_savings": round(cost_savings),
        "road_total": round(road_total), "sea_total": round(sea_total),
    }
    save_history(record)

    return {
        "record_id": record["id"],
        "distance": round(base,2), "road_distance": rd, "sea_distance": sd,
        "containers": containers, "ship_date": ship_date,
        "start_name": p1["name"], "end_name": p2["name"],
        "start_lat": p1["lat"], "start_lon": p1["lon"],
        "end_lat": p2["lat"], "end_lon": p2["lon"],
        "road": {"freight": round(road_freight), "carbon": round(road_carbon,2), "total": round(road_total)},
        "sea": {"freight": round(sea_freight), "carbon": round(sea_carbon,2), "total": round(sea_total)},
        "best_mode": best_mode, "cost_savings": round(cost_savings),
        "carbon_improvement": round(carbon_improvement,2), "reduction_pct": round(reduction_pct,1),
        "road_condition": {
            "level": rc["level"],
            "level_text": "順暢" if rc["level"]=="low" else ("車多" if rc["level"]=="medium" else "壅塞"),
            "avg_speed": rc["avg_speed"], "nh1_speed": rc["nh1_speed"], "nh3_speed": rc["nh3_speed"]
        },
        "ship_schedule": ss,
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
    token = get_tdx_token()
    segments = ["NH1-N-0","NH1-S-1","NH1-S-2","NH1-S-3","NH1-S-4","NH3-N-0","NH3-S-1","NH3-S-2","NH3-S-3","NH3-S-4","NH3-S-5","NH5-S-0"]
    if not token:
        return jsonify([{"id": s, "speed": 55} for s in segments])
    try:
        res = requests.get("https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON", headers={"authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            speeds = [i["Speed"] for i in res.json().get("Data",[]) if "Speed" in i]
            if speeds:
                return jsonify([{"id": segments[i%len(segments)], "speed": speeds[i%len(speeds)]} for i in range(len(segments))])
    except:
        pass
    return jsonify([{"id": s, "speed": 55} for s in segments])

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")
    containers = data.get("containers")
    ship_date = data.get("ship_date", "")
    if start not in PORTS or end not in PORTS: return jsonify({"error": "港口代碼無效"}), 400
    if start == end: return jsonify({"error": "起點與終點不可相同"}), 400
    try: containers = int(containers)
    except: return jsonify({"error": "貨櫃數量格式錯誤"}), 400
    if containers <= 0 or containers > 5000: return jsonify({"error": "貨櫃數量需介於 1 到 5000 之間"}), 400
    try:
        return jsonify(build_calculation_result(start, end, containers, ship_date))
    except Exception as e:
        return jsonify({"error": f"計算失敗: {str(e)}"}), 500

@app.route("/certificate", methods=["POST"])
def create_certificate():
    data = request.get_json(silent=True) or {}
    record_id = data.get("record_id")
    company_name = (data.get("company_name") or "").strip()
    if not company_name: return jsonify({"error": "請輸入公司名稱"}), 400
    if not record_id: return jsonify({"error": "缺少計算紀錄 ID"}), 400
    record = get_history_record(record_id)
    if not record: return jsonify({"error": "查無對應的計算紀錄"}), 404
    cert_id = generate_certificate_id()
    cert = {"cert_id": cert_id, "company_name": company_name, "issued_at": datetime.now().strftime("%Y-%m-%d"), "record_id": record_id, "record": record}
    save_certificate(cert)
    return jsonify({"cert_id": cert_id, "company_name": company_name, "issued_at": cert["issued_at"], "route": f"{record['start']} → {record['end']}", "containers": record["containers"], "carbon_improvement": record["carbon_improvement"], "reduction_pct": record["reduction_pct"]})

@app.route("/download_certificate/<cert_id>/<lang>")
def download_certificate(cert_id, lang):
    cert = get_certificate(cert_id)
    if not cert: return jsonify({"error": "查無證書"}), 404
    lang = "en" if lang == "en" else "zh"
    buf = build_certificate_pdf(cert, lang=lang)
    return send_file(buf, as_attachment=True, download_name=f"certificate_{cert_id}_{'english' if lang=='en' else 'chinese'}.pdf", mimetype="application/pdf")

@app.route("/verify/<cert_id>")
def verify_certificate(cert_id):
    cert = get_certificate(cert_id)
    return render_template("verify.html", valid=bool(cert), cert=cert, app_title=APP_TITLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)