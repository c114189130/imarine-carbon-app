import os, math, requests
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

# ================= TDX =================
def get_tdx_token():
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET: return None
    try:
        r = requests.post(
            "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
            data={"grant_type":"client_credentials","client_id":TDX_CLIENT_ID,"client_secret":TDX_CLIENT_SECRET},
            timeout=TIMEOUT)
        if r.status_code==200: return r.json()["access_token"]
    except: pass
    return None

def get_highway_traffic():
    """取得國道即時路況 → 壅塞程度"""
    token = get_tdx_token()
    if not token: return {"nh1":58,"nh3":52,"avg":55,"level":"medium"}
    try:
        r = requests.get(
            "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON",
            headers={"authorization":f"Bearer {token}"}, timeout=TIMEOUT)
        if r.status_code==200:
            data = r.json()
            nh1, nh3 = [], []
            for it in data.get("Data",[]):
                if "Speed" not in it: continue
                vd = it.get("VDID","")
                (nh1 if "NH1" in vd or "N1" in vd else nh3).append(it["Speed"])
            n1 = round(sum(nh1)/len(nh1),1) if nh1 else 50
            n3 = round(sum(nh3)/len(nh3),1) if nh3 else 50
            avg = round((sum(nh1)+sum(nh3))/(len(nh1)+len(nh3)),1) if (nh1 or nh3) else 50
            level = "low" if avg>=60 else ("medium" if avg>=35 else "high")
            return {"nh1":n1,"nh3":n3,"avg":avg,"level":level}
    except: pass
    return {"nh1":58,"nh3":52,"avg":55,"level":"medium"}

# ================= 船班查詢 =================
def find_ships(start_code, end_code, target_date, containers_feu):
    """從目標到貨日反向查詢可用船班"""
    ships = SHIP_SCHEDULE.get(start_code, [])
    candidates = []
    for days_back in range(7, -1, -1):
        check = target_date - timedelta(days=days_back)
        wd = check.weekday()  # 0=Mon
        for ship in ships:
            if ship["dest"] != end_code: continue
            if wd not in ship["weekdays"]: continue
            etd = check.replace(hour=ship["etd_hour"], minute=0)
            eta = etd + timedelta(hours=ship["hours"])
            if eta <= target_date + timedelta(hours=12):  # 容許半天緩衝
                wname = ["一","二","三","四","五","六","日"][wd]
                candidates.append({
                    "ship": f"{ship['name']}({ship['en']})",
                    "weekday": f"週{wname}",
                    "etd": etd.strftime("%m/%d %H:%M"),
                    "eta": eta.strftime("%m/%d %H:%M"),
                    "hours": ship["hours"],
                    "capacity": ship["capacity_feu"],
                    "fits": True
                })
    return candidates[:4]

# ================= 核心計算 =================
def calculate_result(start, end, containers, unit, target_date_str):
    # --- TEU/FEU ---
    if unit == "TEU":
        cf = float(containers) * TEU_TO_FEU
        cdisp = f"{containers} TEU ({cf:.1f} FEU)"
    else:
        cf = float(containers)
        cdisp = f"{containers} FEU"

    p1, p2 = PORTS[start], PORTS[end]
    route = ROUTES.get((start,end), {"road_km":200,"sea_km":160})
    rkm, skm = route["road_km"], route["sea_km"]

    # --- 路況 ---
    traffic = get_highway_traffic()
    cfactor = CONGESTION_FACTOR.get(traffic["level"], 1.0)
    road_hours = round(rkm / ROAD_SPEED_KMH * cfactor, 1)

    # --- 時間 ---
    try: target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    except: target_dt = datetime.now() + timedelta(days=7)

    now = datetime.now()
    road_eta = now + timedelta(hours=road_hours)
    road_ok = road_eta <= target_dt + timedelta(hours=12)

    ship_list = find_ships(p1["code"], end, target_dt, cf)
    best_ship = ship_list[0] if ship_list else None
    sea_ok = best_ship is not None

    # --- 碳排 ---
    road_carbon = EMISSION_FACTORS["road"] * rkm * cf
    sea_carbon = EMISSION_FACTORS["sea"] * skm * cf + PORT_HANDLING_EMISSION * cf * 2

    # --- 成本 ---
    road_cost = TRANSPORT_COST_RATES["road"] * rkm * cf + ROAD_TOLL_RATE * rkm * cf
    sea_cost = TRANSPORT_COST_RATES["sea"] * skm * cf + PORT_HANDLING_FEE * cf

    road_total = road_cost
    sea_total = sea_cost

    # --- 碳費（外部成本） ---
    road_carbon_fee = road_carbon * CARBON_PRICE_PER_KG
    sea_carbon_fee = sea_carbon * CARBON_PRICE_PER_KG

    road_full_cost = road_total + road_carbon_fee
    sea_full_cost = sea_total + sea_carbon_fee

    # --- 改善量 ---
    carbon_saved = road_carbon - sea_carbon   # 正=海運減碳
    carbon_pct = round(carbon_saved/road_carbon*100,1) if road_carbon>0 else 0
    carbon_credit = round(carbon_saved * CARBON_PRICE_PER_KG, 2)

    cost_saved = road_full_cost - sea_full_cost

    # --- 決策 ---
    reasons = []
    if sea_ok and sea_full_cost < road_full_cost:
        decision = "海轉（藍色公路）"
        reasons.append("✅ 船班可於目標日前抵達")
        reasons.append(f"💰 海運總成本（含碳費）較陸拖節省 NT$ {abs(cost_saved):,.0f}")
        reasons.append(f"🌱 海運減碳 {carbon_saved:.0f} kg CO2e（-{carbon_pct}%）")
    elif sea_ok and not road_ok:
        decision = "海轉（藍色公路）"
        reasons.append("⚠️ 陸拖無法於目標日前抵達，海運為唯一選項")
    elif road_ok and (not sea_ok or road_full_cost <= sea_full_cost):
        decision = "陸拖（公路運輸）"
        if not sea_ok: reasons.append("❌ 無合適船班可於目標日前抵達")
        else: reasons.append("💰 陸拖總成本（含碳費）較海運低或相當")
    elif not road_ok and not sea_ok:
        decision = "無法滿足（建議調整目標日）"
        reasons.append("❌ 海陸方案皆無法於目標日前抵達，請放寬到貨日")
    else:
        decision = "海轉（藍色公路）"
        reasons.append("綜合評估後海運較優")

    # --- 存記錄 ---
    rec = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S")+uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"], "end": p2["name"],
        "containers": containers, "unit": unit, "cf": round(cf,1),
        "target": target_date_str, "rkm": rkm, "skm": skm,
        "rc": round(road_carbon,2), "sc": round(sea_carbon,2),
        "ci": round(carbon_saved,2), "rp": carbon_pct, "cc": carbon_credit,
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
            "carbon": round(road_carbon,2), "total": round(road_full_cost)
        },
        "sea": {
            "freight": round(sea_cost), "carbon_fee": round(sea_carbon_fee),
            "carbon": round(sea_carbon,2), "total": round(sea_full_cost)
        },
        "carbon_saved": round(carbon_saved,2),
        "carbon_pct": carbon_pct,
        "carbon_credit": carbon_credit,
        "decision": decision,
        "reasons": reasons,
        "traffic": {
            "nh1": traffic["nh1"], "nh3": traffic["nh3"],
            "avg": traffic["avg"],
            "level": traffic["level"],
            "level_text": "順暢" if traffic["level"]=="low" else ("車多" if traffic["level"]=="medium" else "壅塞")
        },
        "ships": ship_list,
    }

# ================= 資料存取 =================
def load_history(): return read_json(HISTORY_FILE, [])
def save_history(r):
    h = load_history(); h.append(r); write_json(HISTORY_FILE, h[-MAX_HISTORY_RECORDS:])
def load_certs(): return read_json(CERTIFICATE_FILE, [])
def save_cert(c):
    rows=load_certs(); rows.append(c); write_json(CERTIFICATE_FILE, rows)
def get_hist(rid):
    for r in load_history():
        if r["id"]==rid: return r
    return None
def get_cert(cid):
    for c in load_certs():
        if c["cert_id"]==cid: return c
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

@app.route("/calculate", methods=["POST"])
def calc():
    d = request.get_json(silent=True) or {}
    s, e = d.get("start"), d.get("end")
    c, u = d.get("containers"), d.get("unit","FEU")
    td = d.get("target_date","")
    if s not in PORTS or e not in PORTS: return jsonify({"error":"港口無效"}),400
    if s==e: return jsonify({"error":"起終點相同"}),400
    try: c=int(c)
    except: return jsonify({"error":"數量錯誤"}),400
    if c<=0 or c>5000: return jsonify({"error":"數量需1~5000"}),400
    try: return jsonify(calculate_result(s,e,c,u,td))
    except Exception as ex: return jsonify({"error":str(ex)}),500

@app.route("/certificate", methods=["POST"])
def create_cert():
    d = request.get_json(silent=True) or {}
    rid, cn = d.get("record_id"), (d.get("company_name") or "").strip()
    if not cn: return jsonify({"error":"請輸入公司名稱"}),400
    if not rid: return jsonify({"error":"缺少ID"}),400
    rec = get_hist(rid)
    if not rec: return jsonify({"error":"查無記錄"}),404
    cid = generate_certificate_id()
    cert = {"cert_id":cid,"company_name":cn,"issued_at":datetime.now().strftime("%Y-%m-%d"),"record_id":rid,"record":rec}
    save_cert(cert)
    return jsonify({"cert_id":cid,"company_name":cn,"route":f"{rec['start']}→{rec['end']}","ci":rec["ci"]})

@app.route("/download_certificate/<cert_id>")
def download_cert(cert_id):
    cert = get_cert(cert_id)
    if not cert: return jsonify({"error":"查無"}),404
    buf = build_certificate_pdf(cert, lang="en")
    return send_file(buf, as_attachment=True, download_name=f"certificate_{cert_id}.pdf", mimetype="application/pdf")

@app.route("/verify/<cert_id>")
def verify(cert_id):
    cert = get_cert(cert_id)
    return render_template("verify.html", valid=bool(cert), cert=cert, app_title=APP_TITLE)

if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=False)