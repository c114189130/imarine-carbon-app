import os
import json
import random
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

from tdx_api import get_live_traffic_speed
from optimization_model import compare_modes, calculate_optimal_transfer_ratio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# ================= 註冊中文字型 (PDF) =================
try:
    pdfmetrics.registerFont(TTFont('MicrosoftJhengHei', 'msjh.ttf'))
    FONT_NAME = 'MicrosoftJhengHei'
except:
    FONT_NAME = 'Helvetica'

# ================= 載入長榮海運船期 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, 'evergreen_schedule.json')
HISTORY_FILE = os.path.join(BASE_DIR, 'history.json')
CERT_FILE = os.path.join(BASE_DIR, 'certificates.json')

def load_evergreen_schedule():
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "KHH": {"port_name": "高雄港", "ships": [{"name": "Evergreen TBS2", "eta_hours": 24, "available": 320, "destination": "台北港", "route": "TBS2", "eta": "FRI"}]},
            "TXG": {"port_name": "台中港", "ships": [{"name": "Evergreen TBS", "eta_hours": 48, "available": 560, "destination": "高雄港", "route": "TBS", "eta": "THU"}]}
        }

EVERGREEN_SCHEDULE = load_evergreen_schedule()

# ================= 參數設定 =================
EMISSION_FACTORS = {"road": 0.06, "sea": 0.02}
COST_RATES = {"road": 60, "sea": 24}
VSL_RATES = {"road": 1.36, "sea": 0.18}
SOCIAL_COST_RATES = {"road": 3.70, "sea": 0.64}
SOCIAL_COST_OF_CARBON = 10.0
PORT_EMISSION_PER_FEU = 100
ROAD_SPEED_KMH = 60
SEA_SPEED_KMH = 46

ports = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.3, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.27, "lon": 120.52, "code": "TXG"}
}

# ================= 輔助函數 =================
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calculate_time_cost(distance_km, mode, containers, time_sensitivity=0.3):
    CARGO_VALUE = 10000000
    INTEREST_RATE = 0.05
    speed = ROAD_SPEED_KMH if mode == "road" else SEA_SPEED_KMH
    hours = distance_km / speed
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier

def get_ship_schedule(start_code, end_name):
    port_data = EVERGREEN_SCHEDULE.get(start_code, {"ships": []})
    for ship in port_data.get("ships", []):
        if ship.get("destination") == end_name:
            return ship
    return {"name": "Evergreen TBS", "eta_hours": 48, "available": 150, "destination": end_name, "route": "TBS", "eta": "THU"}

def calculate_ai_scores(road_data, ship_data, containers):
    score_sea = 0
    congestion_scores = {"low": 0, "medium": 2, "high": 5}
    score_sea += congestion_scores.get(road_data.get("level", "low"), 0) * 0.6
    if ship_data.get("eta_hours", 24) <= 6:
        score_sea += 3
    elif ship_data.get("eta_hours", 24) <= 12:
        score_sea += 1.5
    if ship_data.get("available", 0) >= containers:
        score_sea += 2
    score_sea += 3.5
    score_sea = min(10, score_sea)
    score_road = min(10, 10 - score_sea + 2)
    return round(score_sea, 1), round(score_road, 1)

def smart_dispatch(containers, road_data, ship_data):
    score_sea, score_road = calculate_ai_scores(road_data, ship_data, containers)
    total = score_sea + score_road
    ratio = 0.5 if total == 0 else max(0.2, min(0.8, score_sea / total))
    to_sea = int(containers * ratio)
    to_road = containers - to_sea
    if to_sea > ship_data.get("available", 999):
        to_sea = ship_data["available"]
        to_road = containers - to_sea
    
    reasons = []
    if road_data.get("level") == "high":
        reasons.append(f"🚨 國道一號目前壅塞（時速 {road_data['avg_speed']} km/h），建議改走海運")
    elif road_data.get("level") == "medium":
        reasons.append(f"⚠️ 國道一號目前車多（時速 {road_data['avg_speed']} km/h）")
    else:
        reasons.append(f"✅ 國道一號目前順暢（時速 {road_data['avg_speed']} km/h）")
    
    if ship_data.get("eta_hours", 24) <= 6:
        reasons.append(f"🚢 長榮海運 {ship_data['name']} 將於 {ship_data['eta_hours']} 小時後抵達，尚有 {ship_data.get('available', 0)} FEU 艙位")
    
    if ratio > 0.6:
        action = "🌊 建議將大部分貨櫃轉為海運"
        suggestion = f"將 {to_sea} FEU 指派給長榮海運 {ship_data['name']}，剩餘 {to_road} FEU 走公路"
    elif ratio < 0.4:
        action = "🚛 建議維持公路運輸"
        suggestion = f"公路運輸較適合，僅 {to_sea} FEU 轉海運"
    else:
        action = "⚖️ 建議平衡分配"
        suggestion = f"海運 {to_sea} FEU、公路 {to_road} FEU 混合運輸"
    
    return {"to_sea": to_sea, "to_road": to_road, "ratio": round(ratio * 100, 1), "score_sea": score_sea, "score_road": score_road, "action": action, "suggestion": suggestion, "reasons": reasons}

# ================= 歷史與證書儲存 =================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_history(record):
    history = load_history()
    history.append(record)
    if len(history) > 50:
        history = history[-50:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_certificates():
    if not os.path.exists(CERT_FILE):
        return []
    try:
        with open(CERT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_certificate(cert_data):
    certs = load_certificates()
    certs.append(cert_data)
    with open(CERT_FILE, 'w', encoding='utf-8') as f:
        json.dump(certs, f, ensure_ascii=False, indent=2)

# ================= 路由 =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/input')
def input_page():
    return render_template('input.html', ports=ports)

@app.route('/result')
def result_page():
    return render_template('result.html')

@app.route('/certificate_page')
def cert_page():
    return render_template('certificate.html')

@app.route('/history_page')
def history_page():
    return render_template('history.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/get_history')
def get_history():
    return jsonify(load_history())

@app.route('/api/traffic')
def api_traffic():
    return jsonify(get_live_traffic_speed())

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少 JSON payload"}), 400
        
        start = data.get('start')
        end = data.get('end')
        containers = data.get('containers')
        
        if start not in ports or end not in ports:
            return jsonify({"error": "無效港口"}), 400
        if start == end:
            return jsonify({"error": "起點與終點不可相同"}), 400
        try:
            containers = int(containers)
            if containers <= 0 or containers > 10000:
                return jsonify({"error": "貨櫃數量超出範圍 (1-10000)"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "貨櫃數量必須為數字"}), 400
        
        p1 = ports[start]
        p2 = ports[end]
        dist = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
        
        road_condition = {"level": random.choice(["low", "medium", "high"]), "avg_speed": random.randint(20, 90)}
        ship_schedule = get_ship_schedule(p1['code'], p2['name'])
        
        road_carbon = EMISSION_FACTORS["road"] * dist * containers
        sea_carbon = EMISSION_FACTORS["sea"] * dist * containers + (PORT_EMISSION_PER_FEU * 2 * containers)
        
        road_freight = COST_RATES["road"] * dist * containers
        sea_freight = COST_RATES["sea"] * dist * containers
        
        road_time = calculate_time_cost(dist, "road", containers)
        sea_time = calculate_time_cost(dist, "sea", containers)
        
        road_social = SOCIAL_COST_RATES["road"] * dist * containers
        sea_social = SOCIAL_COST_RATES["sea"] * dist * containers
        
        road_vsl = VSL_RATES["road"] * dist * containers
        sea_vsl = VSL_RATES["sea"] * dist * containers
        
        road_total = road_freight + road_time + road_social + road_vsl
        sea_total = sea_freight + sea_time + sea_social + sea_vsl
        
        road_total_social = road_total + (road_carbon * SOCIAL_COST_OF_CARBON)
        sea_total_social = sea_total + (sea_carbon * SOCIAL_COST_OF_CARBON)
        
        if sea_total_social < road_total_social:
            best_mode = "海運"
            improvement = road_total_social - sea_total_social
            carbon_improvement = road_carbon - sea_carbon
            reduction_pct = (carbon_improvement / road_carbon) * 100 if road_carbon > 0 else 0
        else:
            best_mode = "公路"
            improvement = sea_total_social - road_total_social
            carbon_improvement = sea_carbon - road_carbon
            reduction_pct = (carbon_improvement / sea_carbon) * 100 if sea_carbon > 0 else 0
        
        dispatch = smart_dispatch(containers, road_condition, ship_schedule)
        optimization = compare_modes(dist, containers)
        optimal_ratio = calculate_optimal_transfer_ratio(dist, containers)
        
        record = {
            "id": datetime.now().strftime('%Y%m%d%H%M%S'),
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "start": ports[start]['name'],
            "end": ports[end]['name'],
            "containers": containers,
            "distance": round(dist, 2),
            "road_carbon": round(road_carbon, 2),
            "sea_carbon": round(sea_carbon, 2),
            "carbon_improvement": round(carbon_improvement, 2),
            "reduction_pct": round(reduction_pct, 1),
            "best_mode": best_mode
        }
        save_history(record)
        
        return jsonify({
            "distance": round(dist, 2),
            "containers": containers,
            "start_name": ports[start]['name'],
            "end_name": ports[end]['name'],
            "start_lat": p1['lat'], "start_lon": p1['lon'],
            "end_lat": p2['lat'], "end_lon": p2['lon'],
            "road": {"freight": round(road_freight), "time": round(road_time), "social": round(road_social), "vsl": round(road_vsl), "carbon": round(road_carbon, 2), "total": round(road_total)},
            "sea": {"freight": round(sea_freight), "time": round(sea_time), "social": round(sea_social), "vsl": round(sea_vsl), "carbon": round(sea_carbon, 2), "total": round(sea_total)},
            "best_mode": best_mode,
            "improvement": round(improvement),
            "carbon_improvement": round(carbon_improvement, 2),
            "reduction_pct": round(reduction_pct, 1),
            "recommendation": f"選擇 {best_mode} 相較替代方案可減少 {carbon_improvement:.0f} kg 碳排放（{reduction_pct:.1f}%）",
            "road_condition": {"level_text": "🟢 順暢" if road_condition["level"]=="low" else "🟡 車多" if road_condition["level"]=="medium" else "🔴 壅塞", "avg_speed": road_condition["avg_speed"]},
            "ship_schedule": ship_schedule,
            "dispatch": dispatch,
            "optimization": optimization,
            "optimal_transfer_ratio": optimal_ratio
        })
    except Exception as e:
        app.logger.error(f"/calculate error: {str(e)}")
        return jsonify({"error": "伺服器內部錯誤"}), 500

@app.route('/certificate', methods=['POST'])
def generate_certificate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少 JSON payload"}), 400
        
        company_name = data.get('name', '').strip()
        if not company_name:
            return jsonify({"error": "請輸入公司名稱"}), 400
        
        carbon_improvement = float(data.get('carbon_saved', 0))
        reduction_pct = float(data.get('reduction_pct', 0))
        
        cert_id = f"CC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        cert_data = {
            "cert_id": cert_id,
            "company_name": company_name,
            "carbon_improvement": round(carbon_improvement, 2),
            "reduction_pct": round(reduction_pct, 1),
            "issued_at": datetime.now().isoformat()
        }
        save_certificate(cert_data)
        
        return jsonify({
            "cert_id": cert_id,
            "name": company_name,
            "date": datetime.now().strftime('%Y年%m月%d日'),
            "carbon_saved": carbon_improvement,
            "reduction_pct": reduction_pct
        })
    except Exception as e:
        app.logger.error(f"/certificate error: {str(e)}")
        return jsonify({"error": "產生證書失敗"}), 500

@app.route('/download_pdf_chinese', methods=['POST'])
def download_pdf_chinese():
    data = request.get_json()
    if not data:
        return jsonify({"error": "缺少資料"}), 400
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=24, textColor=colors.HexColor('#03045e'), alignment=1, spaceAfter=30, fontName=FONT_NAME)
    cert_style = ParagraphStyle('Cert', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#023e8a'), spaceAfter=12, fontName=FONT_NAME)
    
    content = [
        Paragraph("🌱 碳排放減量證明書", title_style),
        Paragraph(f"證書編號：{data['cert_id']}", cert_style),
        Paragraph(f"核發日期：{data.get('date', datetime.now().strftime('%Y年%m月%d日'))}", cert_style),
        Spacer(1, 20),
        Paragraph(f"茲證明 {data['name']} 完成運輸碳排放評估", cert_style),
        Spacer(1, 20),
        Paragraph("📊 計算依據：", cert_style),
        Paragraph("• ISO 14064 原則", cert_style),
        Paragraph("• GLEC Framework（物流碳排）", cert_style),
        Paragraph("• DEFRA emission factors", cert_style),
        Paragraph("• 台灣環境部碳費參考", cert_style),
        Spacer(1, 20),
        Paragraph(f"• 減少碳排放：{data.get('carbon_saved', 0):.2f} kg CO2e", cert_style),
        Paragraph(f"• 減碳比例：{data.get('reduction_pct', 0)}%", cert_style),
        Spacer(1, 30),
        Paragraph("特此證明", cert_style),
        Paragraph("iMarine 智慧海運碳排認證中心", cert_style)
    ]
    doc.build(content)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"certificate_{data['cert_id']}_chinese.pdf", mimetype='application/pdf')

@app.route('/download_pdf_english', methods=['POST'])
def download_pdf_english():
    data = request.get_json()
    if not data:
        return jsonify({"error": "缺少資料"}), 400
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=24, textColor=colors.HexColor('#03045e'), alignment=1, spaceAfter=30, fontName=FONT_NAME)
    cert_style = ParagraphStyle('Cert', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#023e8a'), spaceAfter=12, fontName=FONT_NAME)
    
    content = [
        Paragraph("🌱 Carbon Emission Reduction Certificate", title_style),
        Paragraph(f"Certificate ID: {data['cert_id']}", cert_style),
        Paragraph(f"Issue Date: {datetime.now().strftime('%Y-%m-%d')}", cert_style),
        Spacer(1, 20),
        Paragraph(f"This certifies that {data['name']} has completed the carbon emission assessment", cert_style),
        Spacer(1, 20),
        Paragraph("📊 Calculation Basis:", cert_style),
        Paragraph("• ISO 14064", cert_style),
        Paragraph("• GLEC Framework", cert_style),
        Paragraph("• DEFRA emission factors", cert_style),
        Paragraph("• Taiwan EPA Carbon Fee", cert_style),
        Spacer(1, 20),
        Paragraph(f"• Carbon Saved: {data.get('carbon_saved', 0):.2f} kg CO2e", cert_style),
        Paragraph(f"• Reduction Rate: {data.get('reduction_pct', 0)}%", cert_style),
        Spacer(1, 30),
        Paragraph("Hereby Certified", cert_style),
        Paragraph("iMarine Carbon Management Center", cert_style)
    ]
    doc.build(content)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"certificate_{data['cert_id']}_english.pdf", mimetype='application/pdf')

@app.route('/verify/<cert_id>')
def verify_certificate(cert_id):
    certs = load_certificates()
    for cert in certs:
        if cert['cert_id'] == cert_id:
            return render_template('verify.html', valid=True, cert=cert)
    return render_template('verify.html', valid=False)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)