import os, math, requests, random
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, render_template, request, send_file

# ✅ 直接從 config 匯入所有東西
from config import *
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.storage_service import ensure_json_file, read_json, write_json

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
TIMEOUT = 8

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])


FREEWAY_DEFINITION = [
    {"id":"NH1-N-1","name":"國一 基隆-台北(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-N-2","name":"國一 台北-桃園(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-N-3","name":"國一 桃園-新竹(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-N-4","name":"國一 新竹-台中(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-N-5","name":"國一 台中-台南(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-N-6","name":"國一 台南-高雄(北)","hw":"NH1","dir":"north"},
    {"id":"NH1-S-1","name":"國一 高雄-台南(南)","hw":"NH1","dir":"south"},
    {"id":"NH1-S-2","name":"國一 台南-台中(南)","hw":"NH1","dir":"south"},
    {"id":"NH1-S-3","name":"國一 台中-新竹(南)","hw":"NH1","dir":"south"},
    {"id":"NH1-S-4","name":"國一 新竹-桃園(南)","hw":"NH1","dir":"south"},
    {"id":"NH1-S-5","name":"國一 桃園-台北(南)","hw":"NH1","dir":"south"},
    {"id":"NH1-S-6","name":"國一 台北-基隆(南)","hw":"NH1","dir":"south"},
    {"id":"NH3-N-1","name":"國三 基隆-台北(北)","hw":"NH3","dir":"north"},
    {"id":"NH3-N-2","name":"國三 台北-新竹(北)","hw":"NH3","dir":"north"},
    {"id":"NH3-N-3","name":"國三 新竹-台中(北)","hw":"NH3","dir":"north"},
    {"id":"NH3-N-4","name":"國三 台中-台南(北)","hw":"NH3","dir":"north"},
    {"id":"NH3-N-5","name":"國三 台南-屏東(北)","hw":"NH3","dir":"north"},
    {"id":"NH3-S-1","name":"國三 屏東-台南(南)","hw":"NH3","dir":"south"},
    {"id":"NH3-S-2","name":"國三 台南-台中(南)","hw":"NH3","dir":"south"},
    {"id":"NH3-S-3","name":"國三 台中-新竹(南)","hw":"NH3","dir":"south"},
    {"id":"NH3-S-4","name":"國三 新竹-台北(南)","hw":"NH3","dir":"south"},
    {"id":"NH3-S-5","name":"國三 台北-基隆(南)","hw":"NH3","dir":"south"},
]

SEGMENT_COORDS = {
    "NH1-N-1":[[25.15,121.75],[25.05,121.55]],"NH1-N-2":[[25.05,121.55],[24.98,121.22]],
    "NH1-N-3":[[24.98,121.22],[24.82,120.97]],"NH1-N-4":[[24.82,120.97],[24.15,120.68]],
    "NH1-N-5":[[24.15,120.68],[23.00,120.38]],"NH1-N-6":[[23.00,120.38],[22.62,120.30]],
    "NH1-S-1":[[22.62,120.30],[23.00,120.38]],"NH1-S-2":[[23.00,120.38],[24.15,120.68]],
    "NH1-S-3":[[24.15,120.68],[24.82,120.97]],"NH1-S-4":[[24.82,120.97],[24.98,121.22]],
    "NH1-S-5":[[24.98,121.22],[25.05,121.55]],"NH1-S-6":[[25.05,121.55],[25.15,121.75]],
    "NH3-N-1":[[25.13,121.78],[24.98,121.55]],"NH3-N-2":[[24.98,121.55],[24.78,120.95]],
    "NH3-N-3":[[24.78,120.95],[24.20,120.62]],"NH3-N-4":[[24.20,120.62],[22.70,120.35]],
    "NH3-N-5":[[22.70,120.35],[22.60,120.32]],"NH3-S-1":[[22.60,120.32],[22.70,120.35]],
    "NH3-S-2":[[22.70,120.35],[24.20,120.62]],"NH3-S-3":[[24.20,120.62],[24.78,120.95]],
    "NH3-S-4":[[24.78,120.95],[24.98,121.55]],"NH3-S-5":[[24.98,121.55],[25.13,121.78]],
}


def get_tdx_token():
    if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET: return None
    try:
        r=requests.post("https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
            data={"grant_type":"client_credentials","client_id":TDX_CLIENT_ID,"client_secret":TDX_CLIENT_SECRET},timeout=TIMEOUT)
        if r.status_code==200: return r.json()["access_token"]
    except: pass
    return None


def get_highway_traffic():
    token=get_tdx_token()
    if not token: return _fallback_traffic()
    try:
        r=requests.get("https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/VD/Freeway?$format=JSON",
            headers={"authorization":f"Bearer {token}"},timeout=TIMEOUT)
        if r.status_code==200:
            data=r.json(); segments={}
            for item in data.get("Data",[]):
                if "Speed" not in item: continue
                vd=item.get("VDID",""); sp=item["Speed"]
                hw="NH1" if("NH1" in vd or"N1" in vd)else("NH3" if("NH3" in vd or"N3" in vd)else None)
                if not hw: continue
                d="north" if"-N" in vd else"south"; k=f"{hw}-{d}"
                if k not in segments: segments[k]=[]
                segments[k].append(sp)
            result={}
            for k,speeds in segments.items(): result[k]=round(sum(speeds)/len(speeds),1)if speeds else 55
            return result
    except: pass
    return _fallback_traffic()


def _fallback_traffic():
    result={}
    for hw in["NH1","NH3"]:
        for d in["north","south"]: result[f"{hw}-{d}"]=random.randint(35,85)
    return result


def find_ships(start_code, end_code, target_date, year=2026):
    all_ships=generate_year_schedule(start_code, end_code, year)
    candidates=[]
    for s in all_ships:
        try:
            etd_dt=datetime.strptime(s["etd"],"%Y/%m/%d %H:%M")
            eta_dt=datetime.strptime(s["eta"],"%Y/%m/%d %H:%M")
        except: continue
        if etd_dt>target_date: continue
        if etd_dt<target_date-timedelta(days=7): continue
        if eta_dt<=target_date+timedelta(hours=12):
            remaining=random.randint(50,700)
            candidates.append({"ship":s["ship"],"etd":etd_dt.strftime("%m/%d %H:%M"),"eta":eta_dt.strftime("%m/%d %H:%M"),"hours":s["hours"],"capacity":s["capacity_feu"],"available":remaining,"fits":True})
    return candidates[:4]


def calculate_result(start, end, containers, unit, target_date_str):
    cf=float(containers)*TEU_TO_FEU if unit=="TEU" else float(containers)
    cdisp=f"{containers} TEU ({cf:.1f} FEU)" if unit=="TEU" else f"{containers} FEU"
    p1,p2=PORTS[start],PORTS[end]
    route=ROUTES.get((start,end),{"road_km":200,"sea_km":160})
    rkm,skm=route["road_km"],route["sea_km"]

    traffic=get_highway_traffic()
    avg=(traffic.get("NH1-north",55)+traffic.get("NH1-south",55)+traffic.get("NH3-north",55)+traffic.get("NH3-south",55))/4
    level="low" if avg>=60 else("medium" if avg>=35 else"high")

    try: target_dt=datetime.strptime(target_date_str,"%Y-%m-%d")
    except: target_dt=datetime.now()+timedelta(days=7)

    ships=find_ships(p1["code"],end,target_dt)
    best_ship=ships[0] if ships else None
    sea_ok=best_ship is not None

    rc=EMISSION_FACTORS["road"]*rkm*cf
    sc=EMISSION_FACTORS["sea"]*skm*cf+PORT_HANDLING_EMISSION*cf*2
    rcost=TRANSPORT_COST_RATES["road"]*rkm*cf+ROAD_TOLL_RATE*rkm*cf
    scost=TRANSPORT_COST_RATES["sea"]*skm*cf+PORT_HANDLING_FEE*cf
    rfull=rcost+rc*CARBON_PRICE_PER_KG
    sfull=scost+sc*CARBON_PRICE_PER_KG
    csaved=rc-sc
    cpct=round(csaved/rc*100,1)if rc>0 else 0
    ccredit=round(csaved*CARBON_PRICE_PER_KG,2)

    reasons=[]
    if sea_ok:
        decision="🚢 海轉（藍色公路）"
        reasons.append(f"✅ 船班可於 {target_date_str} 前抵達")
        reasons.append(f"💰 海運 NT$ {sfull:,.0f} vs 陸拖 NT$ {rfull:,.0f}")
        reasons.append(f"🌱 減碳 {csaved:.0f} kg CO2e（-{cpct}%）")
        reasons.append(f"💵 碳權價值 NT$ {ccredit:,.0f}")
    else:
        decision="🚛 陸拖（公路運輸）"
        reasons.append("❌ 目標日前無合適船班")

    rec={"id":datetime.now().strftime("%Y%m%d%H%M%S")+uuid4().hex[:4],"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"start":p1["name"],"end":p2["name"],"containers":containers,"unit":unit,"cf":round(cf,1),"target":target_date_str,"rkm":rkm,"skm":skm,"rc":round(rc,2),"sc":round(sc,2),"ci":round(csaved,2),"rp":cpct,"cc":ccredit,"decision":decision,"rf":round(rcost),"sf":round(scost)}
    save_history(rec)

    return {"record_id":rec["id"],"start_name":p1["name"],"end_name":p2["name"],"start_lat":p1["lat"],"start_lon":p1["lon"],"end_lat":p2["lat"],"end_lon":p2["lon"],"containers":cdisp,"target_date":target_date_str,"road_km":rkm,"sea_km":skm,"road":{"freight":round(rcost),"carbon":round(rc,2),"total":round(rfull)},"sea":{"freight":round(scost),"carbon":round(sc,2),"total":round(sfull)},"carbon_saved":round(csaved,2),"carbon_pct":cpct,"carbon_credit":ccredit,"decision":decision,"reasons":reasons,"traffic":{"avg":round(avg,1),"level":level,"text":"順暢"if level=="low"else("車多"if level=="medium"else"壅塞")},"ships":ships}


def load_history(): return read_json(HISTORY_FILE,[])
def save_history(r):
    h=load_history();h.append(r);write_json(HISTORY_FILE,h[-MAX_HISTORY_RECORDS:])
def load_certs(): return read_json(CERTIFICATE_FILE,[])
def save_cert(c):
    rows=load_certs();rows.append(c);write_json(CERTIFICATE_FILE,rows)
def get_hist(rid):
    for r in load_history():
        if r["id"]==rid: return r
    return None
def get_cert(cid):
    for c in load_certs():
        if c["cert_id"]==cid: return c
    return None


@app.route("/") ; def index(): return render_template("index.html",app_title=APP_TITLE)
@app.route("/input") ; def input_page(): return render_template("input.html",ports=PORTS,app_title=APP_TITLE)
@app.route("/result") ; def result_page(): return render_template("result.html",app_title=APP_TITLE)
@app.route("/certificate_page") ; def cert_page(): return render_template("certificate.html",app_title=APP_TITLE)
@app.route("/history_page") ; def hist_page(): return render_template("history.html",app_title=APP_TITLE)
@app.route("/dashboard") ; def dash_page(): return render_template("dashboard.html",app_title=APP_TITLE)
@app.route("/get_history") ; def api_hist(): return jsonify(load_history())

@app.route("/api/traffic_segments")
def api_traffic_segments():
    traffic=get_highway_traffic();result=[]
    for seg in FREEWAY_DEFINITION:
        k=f"{seg['hw']}-{seg['dir']}";base=traffic.get(k,55)
        speed=max(20,min(100,int(base)+random.randint(-8,8)))
        level="low" if speed>=60 else("medium" if speed>=35 else"high")
        coords=SEGMENT_COORDS.get(seg["id"],[[25,121],[25,121]])
        result.append({"id":seg["id"],"name":seg["name"],"hw":seg["hw"],"dir":seg["dir"],"speed":speed,"level":level,"coords":coords})
    return jsonify(result)

@app.route("/calculate",methods=["POST"])
def calc():
    d=request.get_json(silent=True) or {}
    s,e,c,u,td=d.get("start"),d.get("end"),d.get("containers"),d.get("unit","FEU"),d.get("target_date","")
    if s not in PORTS or e not in PORTS: return jsonify({"error":"港口無效"}),400
    if s==e: return jsonify({"error":"起終點相同"}),400
    try: c=int(c)
    except: return jsonify({"error":"數量錯誤"}),400
    if c<=0 or c>5000: return jsonify({"error":"數量需1~5000"}),400
    try: return jsonify(calculate_result(s,e,c,u,td))
    except Exception as ex: return jsonify({"error":str(ex)}),500

@app.route("/certificate",methods=["POST"])
def create_cert():
    d=request.get_json(silent=True) or {}
    rid,cn=d.get("record_id"),(d.get("company_name") or "").strip()
    if not cn: return jsonify({"error":"請輸入公司名稱"}),400
    if not rid: return jsonify({"error":"缺少ID"}),400
    rec=get_hist(rid)
    if not rec: return jsonify({"error":"查無記錄"}),404
    cid=generate_certificate_id()
    cert={"cert_id":cid,"company_name":cn,"issued_at":datetime.now().strftime("%Y-%m-%d"),"record_id":rid,"record":rec}
    save_cert(cert)
    return jsonify({"cert_id":cid,"company_name":cn,"route":f"{rec['start']}→{rec['end']}","ci":rec["ci"]})

@app.route("/download_certificate/<cert_id>")
def download_cert(cert_id):
    cert=get_cert(cert_id)
    if not cert: return jsonify({"error":"查無"}),404
    buf=build_certificate_pdf(cert,lang="en")
    return send_file(buf,as_attachment=True,download_name=f"certificate_{cert_id}.pdf",mimetype="application/pdf")

@app.route("/verify/<cert_id>")
def verify(cert_id):
    cert=get_cert(cert_id)
    return render_template("verify.html",valid=bool(cert),cert=cert,app_title=APP_TITLE)


if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port,debug=False)