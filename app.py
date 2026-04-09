from flask import Flask, render_template, request, jsonify, send_file
import random
from datetime import datetime
import math
import json
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

# 導入 TDX API
from tdx_api import get_road_congestion, get_live_network_traffic

# ================= 建立 Flask 應用 =================
app = Flask(__name__)

# ================= 載入長榮海運船期 =================
def load_evergreen_schedule():
    try:
        with open('evergreen_schedule.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("錯誤：找不到 evergreen_schedule.json 檔案")
        return {
            "KHH": {"port_name": "高雄港", "ships": []},
            "TXG": {"port_name": "台中港", "ships": []}
        }
    except json.JSONDecodeError as e:
        print(f"錯誤：evergreen_schedule.json 格式錯誤 - {e}")
        return {
            "KHH": {"port_name": "高雄港", "ships": []},
            "TXG": {"port_name": "台中港", "ships": []}
        }

EVERGREEN_SCHEDULE = load_evergreen_schedule()

# ================= 參數設定 =================
EMISSION_FACTORS = {"road": 0.06, "sea": 0.02}
COST_RATES = {"road": 60, "sea": 24}
VSL_RATES = {"road": 1.36, "sea": 0.18}
SOCIAL_COST_RATES = {"road": 3.70, "sea": 0.64}
SOCIAL_COST_OF_CARBON = 10.0
FIXED_PORT_EMISSION = 100

# ================= 貨物類型 =================
CARGO_TYPES = {
    "general": {
        "name": "一般貨物",
        "time_sensitivity": 0.3,
        "urgent_multiplier": 1.0,
        "description": "無特殊時效要求，可接受海運",
        "icon": "📦"
    }
}

# 港口資料
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

def calculate_time_cost(distance_km, mode, containers, time_sensitivity):
    CARGO_VALUE = 10000000
    INTEREST_RATE = 0.05
    if mode == "road":
        hours = distance_km / 60
    else:
        hours = distance_km / 46
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier

def get_ship_schedule(port_code):
    """從長榮海運資料獲取船期"""
    port_data = EVERGREEN_SCHEDULE.get(port_code, {"ships": []})
    if port_data["ships"]:
        return port_data["ships"][0]
    return {
        "name": "Evergreen TBS",
        "eta_hours": 48,
        "available": 150,
        "destination": "高雄港",
        "type": "貨櫃船",
        "service": "Taiwan Strait Blue Way Service"
    }

def calculate_ai_scores(road_data, ship_data, containers):
    score_sea = 0
    score_road = 0
    
    congestion_scores = {"low": 0, "medium": 2, "high": 5}
    score_sea += congestion_scores.get(road_data.get("level", "low"), 0) * 0.6
    
    if ship_data.get("eta_hours", 24) <= 6:
        score_sea += 3
    elif ship_data.get("eta_hours", 24) <= 12:
        score_sea += 1.5
    
    available = ship_data.get("available", 0)
    if available >= containers:
        score_sea += 2
    
    score_sea += 3.5
    score_sea = min(10, score_sea)
    score_road = min(10, 10 - score_sea + 2)
    
    return round(score_sea, 1), round(score_road, 1)

def smart_dispatch(containers, road_data, ship_data):
    score_sea, score_road = calculate_ai_scores(road_data, ship_data, containers)
    
    total = score_sea + score_road
    if total == 0:
        ratio = 0.5
    else:
        ratio = score_sea / total
    ratio = max(0.2, min(0.8, ratio))
    
    to_sea = int(containers * ratio)
    to_road = containers - to_sea
    
    if to_sea > ship_data.get("available", 999):
        to_sea = ship_data["available"]
        to_road = containers - to_sea
    
    reasons = []
    if road_data.get("level") == "high":
        reasons.append(f"🚨 國道一號目前壅塞（時速 {road_data['avg_speed']} km/h），建議改走海運避開車潮")
    elif road_data.get("level") == "medium":
        reasons.append(f"⚠️ 國道一號目前車多（時速 {road_data['avg_speed']} km/h），海運可節省時間")
    else:
        reasons.append(f"✅ 國道一號目前順暢（時速 {road_data['avg_speed']} km/h）")
    
    if ship_data.get("eta_hours", 24) <= 6:
        reasons.append(f"🚢 長榮海運 {ship_data['name']} 將於 {ship_data['eta_hours']} 小時後抵達 {ship_data.get('destination', '港口')}，尚有 {ship_data.get('available', 0)} FEU 艙位")
    elif ship_data.get("eta_hours", 24) <= 12:
        reasons.append(f"⏳ 長榮海運 {ship_data['name']} 將於 {ship_data['eta_hours']} 小時後抵達，艙位充足")
    
    if containers > ship_data.get("available", 999):
        reasons.append(f"⚠️ 貨櫃數量超過可用艙位，建議部分仍走公路")
    
    if ratio > 0.6:
        action = "🌊 建議將大部分貨櫃轉為海運"
        suggestion = f"將 {to_sea} FEU 指派給長榮海運 {ship_data['name']}，剩餘 {to_road} FEU 走公路"
    elif ratio < 0.4:
        action = "🚛 建議維持公路運輸"
        suggestion = f"公路運輸較適合，僅 {to_sea} FEU 轉海運"
    else:
        action = "⚖️ 建議平衡分配"
        suggestion = f"海運 {to_sea} FEU、公路 {to_road} FEU 混合運輸"
    
    return {
        "to_sea": to_sea,
        "to_road": to_road,
        "ratio": round(ratio * 100, 1),
        "score_sea": score_sea,
        "score_road": score_road,
        "action": action,
        "suggestion": suggestion,
        "reasons": reasons,
        "recommended_ship": ship_data["name"] if to_sea > 0 else None
    }

# ================= 歷史記錄 =================
HISTORY_FILE = "history.json"

def save_history(record):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    history.append(record)
    if len(history) > 50:
        history = history[-50:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ================= 路由（API 端點） =================

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

# ⭐ 即時路網 API（1968 等級）
@app.route('/api/traffic')
def api_traffic():
    """即時路網車流 API"""
    roads = get_live_network_traffic()
    return jsonify(roads)

# ⭐ 核心計算路由
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    start = data['start']
    end = data['end']
    containers = int(data['containers'])
    
    cargo = CARGO_TYPES["general"]
    time_sensitivity = cargo["time_sensitivity"]
    urgency_multiplier = cargo["urgent_multiplier"]
    
    p1 = ports[start]
    p2 = ports[end]
    dist = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
    
    road_condition = get_road_congestion(use_api=False)
    ship_schedule = get_ship_schedule(p2['code'])
    
    road_carbon = EMISSION_FACTORS["road"] * dist * containers
    sea_carbon = EMISSION_FACTORS["sea"] * dist * containers + (FIXED_PORT_EMISSION * 2 * containers)
    
    road_freight = COST_RATES["road"] * dist * containers
    sea_freight = COST_RATES["sea"] * dist * containers * urgency_multiplier
    
    road_time = calculate_time_cost(dist, "road", containers, time_sensitivity)
    sea_time = calculate_time_cost(dist, "sea", containers, time_sensitivity)
    
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
        social_savings = road_total_social - sea_total_social
    else:
        best_mode = "公路"
        social_savings = sea_total_social - road_total_social
    
    carbon_saved = road_carbon - sea_carbon
    reduction_pct = (carbon_saved / road_carbon) * 100 if road_carbon > 0 else 0
    
    dispatch = smart_dispatch(containers, road_condition, ship_schedule)
    
    road_result = {
        "freight": round(road_freight),
        "time": round(road_time),
        "social": round(road_social),
        "vsl": round(road_vsl),
        "carbon": round(road_carbon, 2),
        "total": round(road_total)
    }
    
    sea_result = {
        "freight": round(sea_freight),
        "time": round(sea_time),
        "social": round(sea_social),
        "vsl": round(sea_vsl),
        "carbon": round(sea_carbon, 2),
        "total": round(sea_total)
    }
    
    recommendation = f"選擇 {best_mode} 可減少 {carbon_saved:.0f} kg 碳排放（{reduction_pct:.1f}%），節省社會成本 NT$ {social_savings:,.0f} 元。{dispatch['action']}"
    
    record = {
        "id": datetime.now().strftime('%Y%m%d%H%M%S'),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "start": ports[start]['name'],
        "end": ports[end]['name'],
        "containers": containers,
        "distance": round(dist, 2),
        "road_carbon": round(road_carbon, 2),
        "sea_carbon": round(sea_carbon, 2),
        "carbon_saved": round(carbon_saved, 2),
        "reduction_pct": round(reduction_pct, 1),
        "best_mode": best_mode
    }
    save_history(record)
    
    return jsonify({
        "distance": round(dist, 2),
        "containers": containers,
        "start_name": ports[start]['name'],
        "end_name": ports[end]['name'],
        "start_lat": p1['lat'],
        "start_lon": p1['lon'],
        "end_lat": p2['lat'],
        "end_lon": p2['lon'],
        "road": road_result,
        "sea": sea_result,
        "best_mode": best_mode,
        "social_savings": round(social_savings),
        "carbon_saved": round(carbon_saved, 2),
        "reduction_pct": round(reduction_pct, 1),
        "recommendation": recommendation,
        "road_condition": road_condition,
        "ship_schedule": ship_schedule,
        "dispatch": dispatch
    })

@app.route('/certificate', methods=['POST'])
def generate_certificate():
    data = request.json
    cert_id = f"CC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    return jsonify({
        "cert_id": cert_id,
        "name": data['name'],
        "date": datetime.now().strftime('%Y年%m月%d日'),
        "carbon_saved": data.get('carbon_saved', 0),
        "reduction_pct": data.get('reduction_pct', 0)
    })

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json
    file_path = "certificate.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#03045e'),
        alignment=1,
        spaceAfter=30
    )
    
    cert_style = ParagraphStyle(
        'CertStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#023e8a'),
        spaceAfter=12
    )
    
    content = []
    content.append(Paragraph("🌱 碳排認證證書", title_style))
    content.append(Spacer(1, 20))
    content.append(Paragraph("茲證明", cert_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>{data['name']}</b>", ParagraphStyle('Bold', parent=cert_style, fontSize=16)))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"於 {data.get('date', datetime.now().strftime('%Y年%m月%d日'))} 完成運輸碳排放評估，認證編號：{data['cert_id']}", cert_style))
    content.append(Spacer(1, 20))
    
    if data.get('carbon_saved', 0) > 0:
        content.append(Paragraph("📊 評估結果摘要：", cert_style))
        content.append(Paragraph(f"• 減少碳排放：<b>{data['carbon_saved']:.2f} kg CO2e</b>", cert_style))
        content.append(Paragraph(f"• 減碳比例：<b>{data.get('reduction_pct', 0)}%</b>", cert_style))
        content.append(Spacer(1, 20))
    
    content.append(Paragraph("📋 計算依據：", cert_style))
    content.append(Paragraph("• CNS 14064-1 組織層級溫室氣體排放盤查標準", cert_style))
    content.append(Paragraph("• 環保署公告溫室氣體排放係數（2023年版）", cert_style))
    content.append(Paragraph("• 交通部運研所《交通建設計畫經濟效益評估手冊》", cert_style))
    content.append(Paragraph("• 長榮海運 TBS/TBS2 藍色公路航線", cert_style))
    content.append(Paragraph("• 交通部 TDX 即時路況 API", cert_style))
    
    content.append(Spacer(1, 30))
    content.append(Paragraph("特此證明", cert_style))
    content.append(Spacer(1, 50))
    content.append(Paragraph("iMarine 智慧海運碳排認證中心", cert_style))
    
    doc.build(content)
    return send_file(file_path, as_attachment=True, download_name=f"certificate_{data['cert_id']}.pdf")

@app.route('/esg_report', methods=['POST'])
def esg_report():
    data = request.json
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🌱 ESG 永續報告書                          ║
╠══════════════════════════════════════════════════════════════╣
║ 報告日期：{datetime.now().strftime('%Y年%m月%d日')}
║ 公司名稱：{data.get('name', '範例公司')}
╠══════════════════════════════════════════════════════════════╣
║ 📊 環境保護 (Environmental)
║   • 本次運輸碳排放減少量：{data.get('carbon_saved', 0):,.2f} kg CO2e
║   • 相當於種樹：{int(data.get('carbon_saved', 0) / 44)} 棵
║
║ 🤝 社會責任 (Social)
║   • 採用 CNS 14064-1 國家標準
║   • 納入 VSL 統計生命價值評估（NT$5,000萬元）
║   • 採用長榮海運 TBS/TBS2 藍色公路航線
║   • 整合交通部 TDX 即時路況
║
║ 🏛️ 公司治理 (Governance)
║   • 碳排放數據可追溯
║   • 符合國際海事組織(IMO)規範
║   • AI 多因子決策模型
╚══════════════════════════════════════════════════════════════╝
"""
    return jsonify({"report": report})

# ================= 啟動應用 =================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)