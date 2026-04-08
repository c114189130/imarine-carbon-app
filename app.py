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

app = Flask(__name__)

# ================= 參數設定 =================
# 碳排放係數 (kg CO2e/FEU-km)
EMISSION_FACTORS = {
    "road": 0.06,
    "sea": 0.02
}

# 運費單價 (NTD/FEU-km)
COST_RATES = {
    "road": 60,
    "sea": 24
}

# VSL 風險成本 (元/FEU-km)
VSL_RATES = {
    "road": 1.36,
    "sea": 0.18
}

# 社會外部成本 (元/FEU-km)
SOCIAL_COST_RATES = {
    "road": 3.70,
    "sea": 0.64
}

# 碳的社會成本 (NTD/kg CO2e)
SOCIAL_COST_OF_CARBON = 10.0

# 港口固定碳排 (kg/FEU)
FIXED_PORT_EMISSION = 100

# ================= 貨物類型 =================
CARGO_TYPES = {
    "general": {
        "name": "一般貨物",
        "time_sensitivity": 0.3,
        "urgent_multiplier": 1.0,
        "description": "無特殊時效要求，可接受海運",
        "icon": "📦"
    },
    "high_value": {
        "name": "高價值電子產品",
        "time_sensitivity": 0.8,
        "urgent_multiplier": 1.5,
        "description": "時間成本極高，建議公路運輸",
        "icon": "💎"
    },
    "perishable": {
        "name": "生鮮/冷鏈貨物",
        "time_sensitivity": 0.95,
        "urgent_multiplier": 2.0,
        "description": "時效要求極高，必須公路運輸",
        "icon": "🍎"
    },
    "bulk": {
        "name": "大宗原物料",
        "time_sensitivity": 0.1,
        "urgent_multiplier": 0.8,
        "description": "適合海運，成本效益最高",
        "icon": "⛰️"
    },
    "just_in_time": {
        "name": "JIT 即時生產",
        "time_sensitivity": 0.9,
        "urgent_multiplier": 1.8,
        "description": "生產線等待成本高，建議公路",
        "icon": "⚙️"
    }
}

# 港口資料
ports = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.3, "code": "KHH"},
    "taichung": {"name": "台中港", "lat": 24.27, "lon": 120.52, "code": "TXG"},
    "keelung": {"name": "基隆港", "lat": 25.15, "lon": 121.75, "code": "KEL"},
    "taipei": {"name": "台北港", "lat": 25.15, "lon": 121.38, "code": "TPE"},
    "hualien": {"name": "花蓮港", "lat": 23.98, "lon": 121.62, "code": "HUN"}
}

# 港口船期資料（模擬）
SHIP_SCHEDULES = {
    "KHH": {"next_hours": random.randint(2, 12), "capacity": random.randint(100, 300)},
    "TXG": {"next_hours": random.randint(3, 15), "capacity": random.randint(80, 200)},
    "KEL": {"next_hours": random.randint(4, 18), "capacity": random.randint(120, 250)},
    "TPE": {"next_hours": random.randint(5, 20), "capacity": random.randint(60, 150)},
    "HUN": {"next_hours": random.randint(6, 24), "capacity": random.randint(40, 100)}
}

# ================= 輔助函數 =================
def haversine_distance(lat1, lon1, lat2, lon2):
    """計算兩點距離 (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calculate_time_cost(distance_km, mode, containers, time_sensitivity):
    """計算時間成本"""
    CARGO_VALUE = 10000000
    INTEREST_RATE = 0.05
    
    if mode == "road":
        hours = distance_km / 60
    else:
        hours = distance_km / 46
    
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier

def get_road_condition():
    """獲取即時路況（模擬）"""
    current_hour = datetime.now().hour
    
    # 尖峰時段容易塞車
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        level = random.choice(["medium", "high"])
    else:
        level = random.choice(["low", "medium"])
    
    speed_map = {"low": random.randint(60, 90), "medium": random.randint(35, 59), "high": random.randint(10, 34)}
    text_map = {"low": "🟢 順暢", "medium": "🟡 車多", "high": "🔴 壅塞"}
    
    return {
        "level": level,
        "level_text": text_map[level],
        "avg_speed": speed_map[level],
        "delay_factor": 1.0 if level == "low" else 1.6 if level == "medium" else 2.5
    }

def get_ship_schedule(port_code):
    """獲取船期資訊"""
    schedule = SHIP_SCHEDULES.get(port_code, {"next_hours": 12, "capacity": 150})
    
    if schedule["next_hours"] <= 3:
        status = "🟢 立即到港"
        urgency = "high"
    elif schedule["next_hours"] <= 8:
        status = "🟡 即將到港"
        urgency = "medium"
    elif schedule["next_hours"] <= 16:
        status = "⏳ 正常"
        urgency = "low"
    else:
        status = "🔴 尚需等待"
        urgency = "very_low"
    
    return {
        "next_hours": schedule["next_hours"],
        "available_capacity": schedule["capacity"],
        "status": status,
        "urgency": urgency
    }

def smart_dispatch(containers, road_condition, ship_schedule, cargo):
    """智慧調度決策"""
    score_sea = 0
    score_road = 0
    
    # 公路壅塞加分
    if road_condition["level"] == "high":
        score_sea += 5
    elif road_condition["level"] == "medium":
        score_sea += 2
    
    # 船期緊急加分
    if ship_schedule["urgency"] == "high":
        score_sea += 5
    elif ship_schedule["urgency"] == "medium":
        score_sea += 3
    
    # 貨物時效性（公路加分）
    score_road += cargo.get("time_sensitivity", 0.3) * 5
    
    # 基礎海運優勢
    score_sea += 2
    
    total = score_sea + score_road
    if total == 0:
        ratio = 0.5
    else:
        ratio = score_sea / total
    
    # 限制比例
    ratio = max(0.2, min(0.8, ratio))
    
    to_sea = int(containers * ratio)
    to_road = containers - to_sea
    
    # 限制艙位容量
    if to_sea > ship_schedule["available_capacity"]:
        to_sea = ship_schedule["available_capacity"]
        to_road = containers - to_sea
    
    # 產生理由
    reasons = []
    if road_condition["level"] == "high":
        reasons.append(f"公路壅塞（時速 {road_condition['avg_speed']} km/h）")
    elif road_condition["level"] == "medium":
        reasons.append(f"公路車多（時速 {road_condition['avg_speed']} km/h）")
    
    if ship_schedule["urgency"] in ["high", "medium"]:
        reasons.append(f"船舶 {ship_schedule['next_hours']} 小時內到港")
    
    if cargo.get("time_sensitivity", 0) > 0.7:
        reasons.append(f"貨物時效性高（敏感度 {cargo['time_sensitivity']*100:.0f}%）")
    
    if ratio > 0.6:
        action = "建議轉海運"
    elif ratio < 0.4:
        action = "建議保留公路"
    else:
        action = "建議平衡分配"
    
    reason = f"AI 評分：海運 {score_sea:.1f} / 公路 {score_road:.1f}，{action}"
    if reasons:
        reason += f"（{', '.join(reasons)}）"
    
    return {
        "to_sea": to_sea,
        "to_road": to_road,
        "ratio": round(ratio * 100, 1),
        "score_sea": round(score_sea, 1),
        "score_road": round(score_road, 1),
        "reason": reason
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

# ================= 路由 =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/input')
def input_page():
    return render_template('input.html', ports=ports, cargo_types=CARGO_TYPES)

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

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    start = data['start']
    end = data['end']
    containers = int(data['containers'])
    cargo_type = data.get('cargo_type', 'general')
    
    cargo = CARGO_TYPES.get(cargo_type, CARGO_TYPES["general"])
    time_sensitivity = cargo["time_sensitivity"]
    urgency_multiplier = cargo["urgent_multiplier"]
    
    p1 = ports[start]
    p2 = ports[end]
    dist = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
    
    # 獲取即時資料
    road_condition = get_road_condition()
    ship_schedule = get_ship_schedule(p2['code'])
    
    # 碳排放計算
    road_carbon = EMISSION_FACTORS["road"] * dist * containers
    sea_carbon = EMISSION_FACTORS["sea"] * dist * containers + (FIXED_PORT_EMISSION * 2 * containers)
    
    # 成本計算
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
    
    # 總體社會成本（含碳損害）
    road_total_social = road_total + (road_carbon * SOCIAL_COST_OF_CARBON)
    sea_total_social = sea_total + (sea_carbon * SOCIAL_COST_OF_CARBON)
    
    # 決策
    if sea_total_social < road_total_social:
        best_mode = "海運"
        social_savings = road_total_social - sea_total_social
    else:
        best_mode = "公路"
        social_savings = sea_total_social - road_total_social
    
    carbon_saved = road_carbon - sea_carbon
    reduction_pct = (carbon_saved / road_carbon) * 100 if road_carbon > 0 else 0
    
    # 智慧調度
    dispatch = smart_dispatch(containers, road_condition, ship_schedule, cargo)
    
    # 結果封裝
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
    
    # 推薦理由
    if best_mode == "海運":
        recommendation = f"經AI評估，選擇海運可減少 {carbon_saved:.0f} kg 碳排放（{reduction_pct:.1f}%），節省社會成本 NT$ {social_savings:,.0f} 元。"
    else:
        recommendation = f"雖然海運可減少 {carbon_saved:.0f} kg 碳排放，但考量貨物 '{cargo['name']}' 的時效性，公路運輸更合適。"
    
    # 儲存歷史
    record = {
        "id": datetime.now().strftime('%Y%m%d%H%M%S'),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "start": ports[start]['name'],
        "end": ports[end]['name'],
        "containers": containers,
        "cargo_type": cargo['name'],
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
        "road": road_result,
        "sea": sea_result,
        "best_mode": best_mode,
        "social_savings": round(social_savings),
        "carbon_saved": round(carbon_saved, 2),
        "reduction_pct": round(reduction_pct, 1),
        "cargo_name": cargo['name'],
        "cargo_icon": cargo['icon'],
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
║
║ 🏛️ 公司治理 (Governance)
║   • 碳排放數據可追溯
║   • 符合國際海事組織(IMO)規範
╚══════════════════════════════════════════════════════════════╝
"""
    return jsonify({"report": report})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)