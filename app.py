import os
import math
import requests
import random
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

from config import *
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.storage_service import ensure_json_file, read_json, write_json

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
TIMEOUT = 8

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])


# ========== 國道路段定義 ==========
FREEWAY_DEFINITION = [
    # 國道一號 北上
    {"id": "NH1-N-1", "name": "基隆-台北", "hw": "NH1", "dir": "north"},
    {"id": "NH1-N-2", "name": "台北-桃園", "hw": "NH1", "dir": "north"},
    {"id": "NH1-N-3", "name": "桃園-新竹", "hw": "NH1", "dir": "north"},
    {"id": "NH1-N-4", "name": "新竹-台中", "hw": "NH1", "dir": "north"},
    {"id": "NH1-N-5", "name": "台中-台南", "hw": "NH1", "dir": "north"},
    {"id": "NH1-N-6", "name": "台南-高雄", "hw": "NH1", "dir": "north"},
    # 國道一號 南下
    {"id": "NH1-S-1", "name": "高雄-台南", "hw": "NH1", "dir": "south"},
    {"id": "NH1-S-2", "name": "台南-台中", "hw": "NH1", "dir": "south"},
    {"id": "NH1-S-3", "name": "台中-新竹", "hw": "NH1", "dir": "south"},
    {"id": "NH1-S-4", "name": "新竹-桃園", "hw": "NH1", "dir": "south"},
    {"id": "NH1-S-5", "name": "桃園-台北", "hw": "NH1", "dir": "south"},
    {"id": "NH1-S-6", "name": "台北-基隆", "hw": "NH1", "dir": "south"},
    # 國道三號 北上
    {"id": "NH3-N-1", "name": "基隆-台北", "hw": "NH3", "dir": "north"},
    {"id": "NH3-N-2", "name": "台北-新竹", "hw": "NH3", "dir": "north"},
    {"id": "NH3-N-3", "name": "新竹-台中", "hw": "NH3", "dir": "north"},
    {"id": "NH3-N-4", "name": "台中-台南", "hw": "NH3", "dir": "north"},
    {"id": "NH3-N-5", "name": "台南-屏東", "hw": "NH3", "dir": "north"},
    # 國道三號 南下
    {"id": "NH3-S-1", "name": "屏東-台南", "hw": "NH3", "dir": "south"},
    {"id": "NH3-S-2", "name": "台南-台中", "hw": "NH3", "dir": "south"},
    {"id": "NH3-S-3", "name": "台中-新竹", "hw": "NH3", "dir": "south"},
    {"id": "NH3-S-4", "name": "新竹-台北", "hw": "NH3", "dir": "south"},
    {"id": "NH3-S-5", "name": "台北-基隆", "hw": "NH3", "dir": "south"},
]


# ================= TDX API =================
def get_tdx_token():
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET:
        return None
    try:
        r = requests.post(
            "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": TDX_CLIENT_ID,
                "client_secret": TDX_CLIENT_SECRET
            },
            timeout=TIMEOUT
        )
        if r.status_code == 200:
            return r.json()["access_token"]
    except:
        pass
    return None


def get_highway_traffic():
    """取得國道 VD 資料，區分北上/南下"""
    token = get_tdx_token()
    if not token:
        return _fallback_traffic()

    try:
        r = requests.get(
            "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON",
            headers={"authorization": f"Bearer {token}"},
            timeout=TIMEOUT
        )
        if r.status_code == 200:
            data = r.json()
            segments = {}
            for item in data.get("Data", []):
                if "Speed" not in item:
                    continue
                vd_id = item.get("VDID", "")
                speed = item["Speed"]
                if "NH1" in vd_id or "N1" in vd_id:
                    hw = "NH1"
                elif "NH3" in vd_id or "N3" in vd_id:
                    hw = "NH3"
                else:
                    continue
                direction = "north" if "-N" in vd_id else "south"
                key = f"{hw}-{direction}"
                if key not in segments:
                    segments[key] = []
                segments[key].append(speed)

            result = {}
            for key, speeds in segments.items():
                result[key] = round(sum(speeds) / len(speeds), 1) if speeds else 55
            return result
    except:
        pass
    return _fallback_traffic()


def _fallback_traffic():
    """動態亂數路況備用資料"""
    result = {}
    for hw in ["NH1", "NH3"]:
        for d in ["north", "south"]:
            key = f"{hw}-{d}"
            result[key] = random.randint(30, 90)
    return result


# ================= 船班查詢 =================
def find_ships(start_code, end_code, target_date, containers_feu):
    ships = SHIP_SCHEDULE.get(start_code, [])
    candidates = []
    for days_back in range(7, -1, -1):
        check = target_date - timedelta(days=days_back)
        wd = check.weekday()
        for ship in ships:
            if ship["dest"] != end_code:
                continue
            if wd not in ship["weekdays"]:
                continue
            etd = check.replace(hour=ship["etd_hour"], minute=0)
            eta = etd + timedelta(hours=ship["hours"])
            if eta <= target_date + timedelta(hours=12):
                remaining = random.randint(
                    int(ship["capacity_feu"] * 0.2),
                    int(ship["capacity_feu"] * 0.95)
                )
                wname = ["一", "二", "三", "四", "五", "六", "日"][wd]
                candidates.append({
                    "ship": f"{ship['name']}({ship['en']})",
                    "weekday": f"週{wname}",
                    "etd": etd.strftime("%m/%d %H:%M"),
                    "eta": eta.strftime("%m/%d %H:%M"),
                    "hours": ship["hours"],
                    "capacity": ship["capacity_feu"],
                    "available": remaining,
                    "fits": remaining >= containers_feu
                })
    return candidates[:4]


# ================= 核心計算 =================
def calculate_result(start, end, containers, unit, target_date_str):
    if unit == "TEU":
        cf = float(containers) * TEU_TO_FEU
        cdisp = f"{containers} TEU ({cf:.1f} FEU)"
    else:
        cf = float(containers)
        cdisp = f"{containers} FEU"

    p1, p2 = PORTS[start], PORTS[end]
    route = ROUTES.get((start, end), {"road_km": 200, "sea_km": 160})
    rkm, skm = route["road_km"], route["sea_km"]

    traffic_data = get_highway_traffic()
    nh1_n = traffic_data.get("NH1-north", 55)
    nh1_s = traffic_data.get("NH1-south", 55)
    avg_speed = (nh1_n + nh1_s) / 2
    cfactor = 1.0
    if avg_speed >= 60:
        cong_level = "low"
    elif avg_speed >= 35:
        cong_level = "medium"
        cfactor = 1.2
    else:
        cong_level = "high"
        cfactor = 1.5

    road_hours = round(rkm / ROAD_SPEED_KMH * cfactor, 1)

    try:
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    except:
        target_dt = datetime.now() + timedelta(days=7)

    now = datetime.now()
    road_eta = now + timedelta(hours=road_hours)
    road_ok = road_eta <= target_dt + timedelta(hours=12)

    ship_list = find_ships(p1["code"], end, target_dt, cf)
    best_ship = ship_list[0] if ship_list else None
    sea_ok = best_ship is not None and best_ship["fits"]

    road_carbon = EMISSION_FACTORS["road"] * rkm * cf
    sea_carbon = EMISSION_FACTORS["sea"] * skm * cf + PORT_HANDLING_EMISSION * cf * 2

    road_cost = TRANSPORT_COST_RATES["road"] * rkm * cf + ROAD_TOLL_RATE * rkm * cf
    sea_cost = TRANSPORT_COST_RATES["sea"] * skm * cf + PORT_HANDLING_FEE * cf

    road_total = road_cost
    sea_total = sea_cost

    road_carbon_fee = road_carbon * CARBON_PRICE_PER_KG
    sea_carbon_fee = sea_carbon * CARBON_PRICE_PER_KG

    road_full = road_total + road_carbon_fee
    sea_full = sea_total + sea_carbon_fee

    carbon_saved = road_carbon - sea_carbon
    carbon_pct = round(carbon_saved / road_carbon * 100, 1) if road_carbon > 0 else 0
    carbon_credit = round(carbon_saved * CARBON_PRICE_PER_KG, 2)

    cost_saved = road_full - sea_full

    reasons = []
    if sea_ok and sea_full < road_full:
        decision = "海轉（藍色公路）"
        reasons.append("✅ 船班可於目標日前抵達")
        reasons.append(f"💰 海運總成本（含碳費）較陸拖節省 NT$ {abs(cost_saved):,.0f}")
        reasons.append(f"🌱 海運減碳 {carbon_saved:.0f} kg CO2e（-{carbon_pct}%）")
    elif sea_ok and not road_ok:
        decision = "海轉（藍色公路）"
        reasons.append("⚠️ 陸拖無法於目標日前抵達，海運為唯一選項")
    elif road_ok and (not sea_ok or road_full <= sea_full):
        decision = "陸拖（公路運輸）"
        if not sea_ok:
            reasons.append("❌ 無合適船班可於目標日前抵達")
        else:
            reasons.append("💰 陸拖總成本（含碳費）較海運低或相當")
    elif not road_ok and not sea_ok:
        decision = "無法滿足（建議調整目標日）"
        reasons.append("❌ 海陸方案皆無法於目標日前抵達，請放寬到貨日")
    else:
        decision = "海轉（藍色公路）"
        reasons.append("綜合評估後海運較優")

    rec = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"], "end": p2["name"],
        "containers": containers, "unit": unit, "cf": round(cf, 1),
        "target": target_date_str, "rkm": rkm, "skm": skm,
        "rc": round(road_carbon, 2), "sc": round(sea_carbon, 2),
        "ci": round(carbon_saved, 2), "rp": carbon_pct, "cc": carbon_credit,
        "decision": decision, "rf": round(road_total), "sf": round(sea_total),
    }
    save_history(rec)

    return {
        "record_id": rec["id"],
        "start_name": p1["name"], "end_name": p2["name"],
        "containers": cdisp, "target_date": target_date_str,
        "road_km": rkm, "sea_km": skm, "road_hours": road_hours,
        "road_eta": road_eta.strftime("%m/%d %H:%M"),
        "road_ok": road_ok, "sea_ok": sea_ok,
        "road": {
            "freight": round(road_cost), "carbon_fee": round(road_carbon_fee),
            "carbon": round(road_carbon, 2), "total": round(road_full)
        },
        "sea": {
            "freight": round(sea_cost), "carbon_fee": round(sea_carbon_fee),
            "carbon": round(sea_carbon, 2), "total": round(sea_full)
        },
        "carbon_saved": round(carbon_saved, 2),
        "carbon_pct": carbon_pct,
        "carbon_credit": carbon_credit,
        "decision": decision,
        "reasons": reasons,
        "traffic": {
            "avg": avg_speed,
            "congestion": cong_level,
            "congestion_text": "順暢" if cong_level == "low" else ("車多" if cong_level == "medium" else "壅塞")
        },
        "ships": ship_list,
    }


# ================= 資料存取 =================
def load_history():
    return read_json(HISTORY_FILE, [])

def save_history(r):
    h = load_history()
    h.append(r)
    write_json(HISTORY_FILE, h[-MAX_HISTORY_RECORDS:])

def load_certs():
    return read_json(CERTIFICATE_FILE, [])

def save_cert(c):
    rows = load_certs()
    rows.append(c)
    write_json(CERTIFICATE_FILE, rows)

def get_hist(rid):
    for r in load_history():
        if r["id"] == rid:
            return r
    return None

def get_cert(cid):
    for c in load_certs():
        if c["cert_id"] == cid:
            return c
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
def cert_page():
    return render_template("certificate.html", app_title=APP_TITLE)

@app.route("/history_page")
def hist_page():
    return render_template("history.html", app_title=APP_TITLE)

@app.route("/dashboard")
def dash_page():
    return render_template("dashboard.html", app_title=APP_TITLE)

@app.route("/get_history")
def api_hist():
    return jsonify(load_history())

@app.route("/api/traffic_segments")
def api_traffic_segments():
    """回傳各路段的即時時速（給前端地圖上色）"""
    traffic = get_highway_traffic()
    result = []
    for seg in FREEWAY_DEFINITION:
        key = f"{seg['hw']}-{seg['dir']}"
        base_speed = traffic.get(key, 55)
        speed = max(20, min(100, int(base_speed) + random.randint(-10, 10)))
        if speed >= 60:
            level = "low"
        elif speed >= 35:
            level = "medium"
        else:
            level = "high"
        result.append({
            "id": seg["id"],
            "name": seg["name"],
            "hw": seg["hw"],
            "dir": seg["dir"],
            "speed": speed,
            "level": level
        })
    return jsonify(result)

@app.route("/calculate", methods=["POST"])
def calc():
    d = request.get_json(silent=True) or {}
    s, e = d.get("start"), d.get("end")
    c, u = d.get("containers"), d.get("unit", "FEU")
    td = d.get("target_date", "")
    if s not in PORTS or e not in PORTS:
        return jsonify({"error": "港口無效"}), 400
    if s == e:
        return jsonify({"error": "起終點相同"}), 400
    try:
        c = int(c)
    except:
        return jsonify({"error": "數量錯誤"}), 400
    if c <= 0 or c > 5000:
        return jsonify({"error": "數量需1~5000"}), 400
    try:
        return jsonify(calculate_result(s, e, c, u, td))
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

@app.route("/certificate", methods=["POST"])
def create_cert():
    d = request.get_json(silent=True) or {}
    rid, cn = d.get("record_id"), (d.get("company_name") or "").strip()
    if not cn:
        return jsonify({"error": "請輸入公司名稱"}), 400
    if not rid:
        return jsonify({"error": "缺少ID"}), 400
    rec = get_hist(rid)
    if not rec:
        return jsonify({"error": "查無記錄"}), 404
    cid = generate_certificate_id()
    cert = {
        "cert_id": cid, "company_name": cn,
        "issued_at": datetime.now().strftime("%Y-%m-%d"),
        "record_id": rid, "record": rec
    }
    save_cert(cert)
    return jsonify({
        "cert_id": cid, "company_name": cn,
        "route": f"{rec['start']}→{rec['end']}",
        "ci": rec["ci"]
    })

@app.route("/download_certificate/<cert_id>")
def download_cert(cert_id):
    cert = get_cert(cert_id)
    if not cert:
        return jsonify({"error": "查無"}), 404
    buf = build_certificate_pdf(cert, lang="en")
    return send_file(buf, as_attachment=True, download_name=f"certificate_{cert_id}.pdf", mimetype="application/pdf")

@app.route("/verify/<cert_id>")
def verify(cert_id):
    cert = get_cert(cert_id)
    return render_template("verify.html", valid=bool(cert), cert=cert, app_title=APP_TITLE)


# ================= 啟動 =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)