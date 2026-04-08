from flask import Flask, render_template, request, jsonify, send_file, session
import random
from datetime import datetime
import math
import json
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

# 導入自訂模組
from data_fetcher import get_sea_route, get_road_data, get_fuel_prices, get_port_capacity
from ai_engine import recommend_v2, normalize

app = Flask(__name__)
app.secret_key = "imarine_secret_key_2024"

# ================= 載入 CNS 標準 =================
def load_emission_standards():
    try:
        with open('emission_standards.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "road": {"value": 0.06, "unit": "kg CO2e/FEU-km", "source": "環保署公告(2023) / 2 (TEU→FEU)", "standard": "CNS 14064-1"},
            "sea": {"value": 0.02, "unit": "kg CO2e/FEU-km", "source": "IMO 國際海事組織 / 2 (TEU→FEU)", "standard": "CNS 14064-1"}
        }

EMISSION_STANDARDS = load_emission_standards()

# ================= 參數設定（FEU 單位） =================
# 基礎碳排係數 (kg CO2e/FEU-km)
BASE_EMISSION_FACTORS = {
    "road": 0.06,
    "sea": 0.02
}

# 運費單價 (NTD/FEU-km)
COST_RATES = {
    "road": 60,      # 公路運費（FEU 約為 TEU 的 2 倍）
    "sea": 24        # 海運運費（FEU 約為 TEU 的 2 倍）
}

VSL_RATES = {
    "road": 1.36,    # VSL風險成本 (元/FEU-km) (TEU的2倍)
    "sea": 0.18
}

SOCIAL_COST_RATES = {
    "road": 3.70,    # 社會外部成本 (元/FEU-km) (TEU的2倍)
    "sea": 0.64
}

# 碳的社會成本 (NTD/kg CO2e)
SOCIAL_COST_OF_CARBON = 10.0

# 港口固定碳排 (kg/FEU)
FIXED_PORT_EMISSION = 100  # FEU 約為 TEU 的 2 倍

# ================= 動態碳排係數調整函數（新增！） =================
def get_dynamic_road_emission(vehicle_type="heavy", load_factor=0.8, road_type="highway"):
    """
    動態計算公路碳排係數 (kg CO2e/FEU-km)
    
    參數:
        vehicle_type: "light"(3.5t), "medium"(12t), "heavy"(35t)
        load_factor: 裝載率 0-1
        road_type: "city"(市區), "highway"(高速), "mixed"(混合)
    """
    base_factors = {
        "light": 0.18,    # 小貨車碳排較高 (kg CO2e/FEU-km)
        "medium": 0.10,
        "heavy": 0.06
    }
    
    road_multipliers = {
        "city": 1.4,      # 市區走走停停，油耗增加40%
        "highway": 1.0,   # 高速公路最省油
        "mixed": 1.2      # 混合路況
    }
    
    factor = base_factors.get(vehicle_type, 0.06)
    factor = factor * road_multipliers.get(road_type, 1.0)
    
    # 裝載率影響：裝載率越高，每 FEU 碳排越低
    # 空車回頭時 load_factor 可能低於 0.5
    adjusted_factor = factor / max(load_factor, 0.3)
    
    return round(adjusted_factor, 4)

def get_dynamic_sea_emission(route_type="short_sea", ship_size="medium"):
    """
    動態計算海運碳排係數 (kg CO2e/FEU-km)
    
    參數:
        route_type: "short_sea"(短程), "deep_sea"(遠洋)
        ship_size: "small"(小), "medium"(中), "large"(大)
    """
    base_factors = {
        "short_sea": 0.03,
        "deep_sea": 0.02
    }
    
    size_multipliers = {
        "small": 1.3,     # 小型船效率較差
        "medium": 1.0,
        "large": 0.8      # 大型船規模經濟
    }
    
    factor = base_factors.get(route_type, 0.02)
    factor = factor * size_multipliers.get(ship_size, 1.0)
    
    return round(factor, 4)

# ================= 貨物類型參數 =================
CARGO_TYPES = {
    "general": {
        "name": "一般貨物",
        "time_sensitivity": 0.3,
        "value_density": 0.3,
        "urgent_multiplier": 1.0,
        "description": "無特殊時效要求，可接受海運",
        "icon": "📦",
        "vehicle_type": "heavy",
        "load_factor": 0.8,
        "road_type": "highway"
    },
    "high_value": {
        "name": "高價值電子產品",
        "time_sensitivity": 0.8,
        "value_density": 0.9,
        "urgent_multiplier": 1.5,
        "description": "時間成本極高，建議公路運輸",
        "icon": "💎",
        "vehicle_type": "medium",
        "load_factor": 0.9,
        "road_type": "highway"
    },
    "perishable": {
        "name": "生鮮/冷鏈貨物",
        "time_sensitivity": 0.95,
        "value_density": 0.7,
        "urgent_multiplier": 2.0,
        "description": "時效要求極高，必須公路運輸",
        "icon": "🍎",
        "vehicle_type": "medium",
        "load_factor": 0.85,
        "road_type": "mixed"
    },
    "bulk": {
        "name": "大宗原物料",
        "time_sensitivity": 0.1,
        "value_density": 0.1,
        "urgent_multiplier": 0.8,
        "description": "適合海運，成本效益最高",
        "icon": "⛰️",
        "vehicle_type": "heavy",
        "load_factor": 0.95,
        "road_type": "highway"
    },
    "just_in_time": {
        "name": "JIT 即時生產",
        "time_sensitivity": 0.9,
        "value_density": 0.6,
        "urgent_multiplier": 1.8,
        "description": "生產線等待成本高，建議公路",
        "icon": "⚙️",
        "vehicle_type": "light",
        "load_factor": 0.7,
        "road_type": "highway"
    }
}

# 港口資料
ports = {
    "kaohsiung": {"name": "高雄港", "lat": 22.616, "lon": 120.3, "code": "KHH", "capacity": 10400000},
    "taichung": {"name": "台中港", "lat": 24.27, "lon": 120.52, "code": "TXG", "capacity": 1800000},
    "keelung": {"name": "基隆港", "lat": 25.15, "lon": 121.75, "code": "KEL", "capacity": 1600000},
    "taipei": {"name": "台北港", "lat": 25.15, "lon": 121.38, "code": "TPE", "capacity": 1800000},
    "hualien": {"name": "花蓮港", "lat": 23.98, "lon": 121.62, "code": "HUN", "capacity": 800000}
}

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calculate_time_cost(distance_km, mode, containers_feu, time_sensitivity=0.3):
    CARGO_VALUE = 10000000  # FEU 貨物價值約為 TEU 的 2 倍
    INTEREST_RATE = 0.05
    
    if mode == "road":
        hours = distance_km / 60
    else:
        hours = distance_km / 46
    
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers_feu * sensitivity_multiplier

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

@app.route('/get_ports')
def get_ports():
    return jsonify(ports)

@app.route('/get_cargo_types')
def get_cargo_types():
    return jsonify(CARGO_TYPES)

@app.route('/get_fuel_prices')
def get_fuel():
    return jsonify(get_fuel_prices())

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    session["user"] = data.get("username", "guest")
    return jsonify({"status": "ok", "user": session["user"]})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({"status": "ok"})

# ================= 主要計算路由（動態碳排版） =================
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    start = data['start']
    end = data['end']
    containers_feu = int(data['containers'])  # 現在單位是 FEU
    cargo_type = data.get('cargo_type', 'general')
    weights = data.get('weights', {"cost": 0.4, "carbon": 0.4, "risk": 0.2})

    cargo = CARGO_TYPES.get(cargo_type, CARGO_TYPES["general"])
    time_sensitivity = cargo["time_sensitivity"]
    urgency_multiplier = cargo["urgent_multiplier"]
    
    # 獲取動態碳排參數
    vehicle_type = cargo.get("vehicle_type", "heavy")
    load_factor = cargo.get("load_factor", 0.8)
    road_type = cargo.get("road_type", "highway")
    
    p1, p2 = ports[start], ports[end]
    dist = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    # 呼叫外部 API
    sea_api = get_sea_route(start, end)
    road_api = get_road_data(start, end)

    # ================= 動態碳排係數計算 =================
    # 根據貨物類型動態調整公路碳排係數
    road_emission_factor = get_dynamic_road_emission(
        vehicle_type=vehicle_type,
        load_factor=load_factor,
        road_type=road_type
    )
    
    # 根據距離動態調整海運碳排係數（短程 vs 遠洋）
    if dist < 300:
        sea_emission_factor = get_dynamic_sea_emission(route_type="short_sea", ship_size="medium")
    else:
        sea_emission_factor = get_dynamic_sea_emission(route_type="deep_sea", ship_size="large")

    # --- 核心碳排放計算（加入港口固定碳排）---
    base_road_carbon = road_emission_factor * dist * containers_feu
    base_sea_carbon = sea_emission_factor * dist * containers_feu
    
    road_carbon = base_road_carbon
    sea_carbon = base_sea_carbon + (FIXED_PORT_EMISSION * 2 * containers_feu)

    # --- 貨幣成本計算 ---
    road_freight = COST_RATES["road"] * dist * containers_feu
    sea_freight = COST_RATES["sea"] * dist * containers_feu * urgency_multiplier

    road_time_cost = calculate_time_cost(dist, "road", containers_feu, time_sensitivity)
    sea_time_cost = calculate_time_cost(dist, "sea", containers_feu, time_sensitivity)

    road_social = SOCIAL_COST_RATES["road"] * dist * containers_feu
    sea_social = SOCIAL_COST_RATES["sea"] * dist * containers_feu

    road_vsl = VSL_RATES["road"] * dist * containers_feu
    sea_vsl = VSL_RATES["sea"] * dist * containers_feu

    road_total_cost = road_freight + road_time_cost + road_social + road_vsl
    sea_total_cost = sea_freight + sea_time_cost + sea_social + sea_vsl

    # --- 總體社會成本（含碳損害）---
    road_total_social_cost = road_total_cost + (road_carbon * SOCIAL_COST_OF_CARBON)
    sea_total_social_cost = sea_total_cost + (sea_carbon * SOCIAL_COST_OF_CARBON)

    # --- 最終決策 ---
    if sea_total_social_cost < road_total_social_cost:
        best_mode = "海運"
        total_social_savings = road_total_social_cost - sea_total_social_cost
    else:
        best_mode = "公路"
        total_social_savings = sea_total_social_cost - road_total_social_cost

    # --- 減碳效益計算（動態）---
    carbon_saved = road_carbon - sea_carbon
    dynamic_reduction_pct = (carbon_saved / road_carbon) * 100 if road_carbon > 0 else 0
    social_savings = road_total_cost - sea_total_cost

    # --- 封裝結果 ---
    road_result = {
        "freight": round(road_freight),
        "time": round(road_time_cost),
        "social": round(road_social),
        "vsl": round(road_vsl),
        "carbon": round(road_carbon, 2),
        "total": round(road_total_cost),
        "emission_factor": road_emission_factor
    }
    
    sea_result = {
        "freight": round(sea_freight),
        "time": round(sea_time_cost),
        "social": round(sea_social),
        "vsl": round(sea_vsl),
        "carbon": round(sea_carbon, 2),
        "total": round(sea_total_cost),
        "emission_factor": sea_emission_factor
    }
    
    best_mode_ai, best_score, all_scores = recommend_v2(road_result, sea_result, weights)
    
    # --- AI 推薦理由 ---
    if best_mode == "海運":
        recommendation_reason = f"經AI評估，選擇海運不僅能減少 {carbon_saved:.0f} kg 碳排放 ({dynamic_reduction_pct:.1f}%)，更能為社會節省總成本 NT$ {total_social_savings:,.0f} 元。"
    else:
        recommendation_reason = f"雖然海運可減少 {carbon_saved:.0f} kg 碳排放，但考量到貨物 '{cargo['name']}' 的高時間價值與急迫性，公路運輸的總體社會成本更低，因此為您推薦公路運輸。"

    # --- 儲存歷史記錄 ---
    record = {
        "id": datetime.now().strftime('%Y%m%d%H%M%S'),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "start": ports[start]['name'],
        "end": ports[end]['name'],
        "containers": containers_feu,
        "unit": "FEU",
        "cargo_type": cargo['name'],
        "distance": round(dist, 2),
        "road_carbon": round(road_carbon, 2),
        "sea_carbon": round(sea_carbon, 2),
        "road_emission_factor": road_emission_factor,
        "sea_emission_factor": sea_emission_factor,
        "carbon_saved": round(carbon_saved, 2),
        "carbon_reduction_pct": round(dynamic_reduction_pct, 1),
        "social_savings": round(social_savings),
        "best_mode": best_mode,
        "weights": weights
    }
    save_history(record)

    return jsonify({
        "distance": round(dist, 2),
        "containers": containers_feu,
        "unit": "FEU",
        "start_name": ports[start]['name'],
        "end_name": ports[end]['name'],
        "start_code": ports[start]['code'],
        "end_code": ports[end]['code'],
        "road": road_result,
        "sea": sea_result,
        "best_mode": best_mode,
        "best_score": best_score,
        "all_scores": all_scores,
        "social_savings": round(social_savings),
        "total_social_savings": round(total_social_savings),
        "carbon_saved": round(carbon_saved, 2),
        "carbon_reduction_pct": round(dynamic_reduction_pct, 1),
        "coords": [[p1['lat'], p1['lon']], [p2['lat'], p2['lon']]],
        "cargo_type": cargo['name'],
        "cargo_icon": cargo['icon'],
        "recommendation_reason": recommendation_reason,
        "time_sensitivity": time_sensitivity,
        "road_emission_factor": road_emission_factor,
        "sea_emission_factor": sea_emission_factor,
        "api_data": {"sea_route": sea_api, "road_data": road_api}
    })

@app.route('/certificate', methods=['POST'])
def generate_certificate():
    data = request.json
    name = data['name']
    carbon_saved = data.get('carbon_saved', 0)
    carbon_reduction_pct = data.get('carbon_reduction_pct', 0)
    
    cert_id = f"CC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    return jsonify({
        "cert_id": cert_id,
        "name": name,
        "date": datetime.now().strftime('%Y年%m月%d日'),
        "carbon_saved": carbon_saved,
        "carbon_reduction_pct": carbon_reduction_pct
    })

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json
    name = data['name']
    cert_id = data['cert_id']
    date = data.get('date', datetime.now().strftime('%Y年%m月%d日'))
    carbon_saved = data.get('carbon_saved', 0)
    carbon_reduction_pct = data.get('carbon_reduction_pct', 0)
    
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
    content.append(Paragraph(f"茲證明", cert_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>{name}</b>", ParagraphStyle('Bold', parent=cert_style, fontSize=16)))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"於 {date} 完成運輸碳排放評估，認證編號：{cert_id}", cert_style))
    content.append(Spacer(1, 20))
    
    if carbon_saved > 0:
        content.append(Paragraph(f"📊 評估結果摘要：", cert_style))
        content.append(Paragraph(f"• 減少碳排放：<b>{carbon_saved:.2f} kg CO2e</b>", cert_style))
        content.append(Paragraph(f"• 減碳比例：<b>{carbon_reduction_pct}%</b>", cert_style))
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
    return send_file(file_path, as_attachment=True, download_name=f"certificate_{cert_id}.pdf")

@app.route('/esg_report', methods=['POST'])
def esg_report():
    data = request.json
    company_name = data.get('name', '範例公司')
    carbon_saved = data.get('carbon_saved', 0)
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🌱 ESG 永續報告書                          ║
╠══════════════════════════════════════════════════════════════╣
║ 報告日期：{datetime.now().strftime('%Y年%m月%d日')}
║ 公司名稱：{company_name}
╠══════════════════════════════════════════════════════════════╣
║ 📊 環境保護 (Environmental)
║   • 本次運輸碳排放減少量：{carbon_saved:,.2f} kg CO2e
║   • 相當於種樹：{int(carbon_saved / 44)} 棵（FEU單位）
║
║ 🤝 社會責任 (Social)
║   • 採用 CNS 14064-1 國家標準
║   • 納入 VSL 統計生命價值評估
║
║ 🏛️ 公司治理 (Governance)
║   • 碳排放數據可追溯
║   • 符合國際海事組織(IMO)規範
╚══════════════════════════════════════════════════════════════╝
"""
    return jsonify({"report": report})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)