import math
from datetime import datetime
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_file

from config import (
    APP_TITLE,
    CERTIFICATE_FILE,
    CARGO_VALUE,
    HISTORY_FILE,
    INTEREST_RATE,
    MAX_HISTORY_RECORDS,
    PORTS,
    PORT_HANDLING_EMISSION_PER_CONTAINER,
    ROAD_SPEED_KMH,
    RISK_COST_RATES,
    SECRET_KEY,
    SEA_SPEED_KMH,
    SOCIAL_COST_OF_CARBON,
    SOCIAL_COST_RATES,
    TRANSPORT_COST_RATES,
    EMISSION_FACTORS,
)
from optimization_model import compare_modes, calculate_optimal_transfer_ratio
from services.certificate_service import build_certificate_pdf, generate_certificate_id
from services.schedule_service import ScheduleService
from services.storage_service import ensure_json_file, read_json, write_json
from services.traffic_service import TrafficService

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

traffic_service = TrafficService()
schedule_service = ScheduleService()

ensure_json_file(HISTORY_FILE, [])
ensure_json_file(CERTIFICATE_FILE, [])


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_route_distance(base_distance_km: float, mode: str) -> float:
    multiplier = 1.22 if mode == "road" else 1.08
    return round(base_distance_km * multiplier, 2)


def calculate_financing_time_cost(distance_km: float, mode: str, containers: int, time_sensitivity: float = 0.3) -> float:
    hours = distance_km / (ROAD_SPEED_KMH if mode == "road" else SEA_SPEED_KMH)
    sensitivity_multiplier = 1 + time_sensitivity * 2
    value_per_hour = (CARGO_VALUE * INTEREST_RATE) / (365 * 24)
    return value_per_hour * hours * containers * sensitivity_multiplier


def calculate_ai_scores(road_data: dict, ship_data: dict, containers: int):
    score_sea = 3.5
    congestion_scores = {"low": 0, "medium": 2, "high": 5}
    score_sea += congestion_scores.get(road_data.get("level", "low"), 0) * 0.6

    eta_hours = ship_data.get("eta_hours", 24)
    if eta_hours <= 6:
        score_sea += 3
    elif eta_hours <= 12:
        score_sea += 1.5
    elif eta_hours <= 24:
        score_sea += 0.8

    if ship_data.get("available", 0) >= containers:
        score_sea += 2
    elif ship_data.get("available", 0) >= containers * 0.5:
        score_sea += 1

    score_sea = min(10, round(score_sea, 1))
    score_road = min(10, round(max(2, 10 - score_sea + 1.5), 1))
    return score_sea, score_road


def smart_dispatch(containers: int, road_data: dict, ship_data: dict):
    score_sea, score_road = calculate_ai_scores(road_data, ship_data, containers)
    total = score_sea + score_road
    ratio = 0.5 if total == 0 else max(0.2, min(0.8, score_sea / total))

    to_sea = int(round(containers * ratio))
    to_road = containers - to_sea
    available = ship_data.get("available", containers)
    if to_sea > available:
        to_sea = available
        to_road = containers - to_sea

    reasons = []
    if road_data.get("level") == "high":
        reasons.append(f"🚨 國道路況壅塞，平均時速 {road_data['avg_speed']} km/h，海運吸引力提高")
    elif road_data.get("level") == "medium":
        reasons.append(f"⚠️ 國道路況偏慢，平均時速 {road_data['avg_speed']} km/h")
    else:
        reasons.append(f"✅ 國道路況順暢，平均時速 {road_data['avg_speed']} km/h")

    reasons.append(
        f"🚢 {ship_data['name']} 預計 {ship_data['eta_hours']} 小時後可銜接，尚有 {ship_data.get('available', 0)} FEU 艙位"
    )

    if ratio >= 0.6:
        action = "🌊 建議以海運為主"
        suggestion = f"海運 {to_sea} FEU、公路 {to_road} FEU，可兼顧成本與容量"
    elif ratio <= 0.4:
        action = "🚛 建議以公路為主"
        suggestion = f"公路 {to_road} FEU、海運 {to_sea} FEU，較適合當前條件"
    else:
        action = "⚖️ 建議混合派遣"
        suggestion = f"海運 {to_sea} FEU、公路 {to_road} FEU，維持彈性"

    return {
        "to_sea": to_sea,
        "to_road": to_road,
        "ratio": round((to_sea / containers) * 100, 1) if containers else 0,
        "score_sea": score_sea,
        "score_road": score_road,
        "action": action,
        "suggestion": suggestion,
        "reasons": reasons,
    }


def load_history() -> list:
    return read_json(HISTORY_FILE, [])


def save_history(record: dict) -> None:
    history = load_history()
    history.append(record)
    history = history[-MAX_HISTORY_RECORDS:]
    write_json(HISTORY_FILE, history)


def load_certificates() -> list:
    return read_json(CERTIFICATE_FILE, [])


def save_certificate(certificate: dict) -> None:
    rows = load_certificates()
    rows.append(certificate)
    write_json(CERTIFICATE_FILE, rows)


def get_history_record(record_id: str):
    for record in load_history():
        if record["id"] == record_id:
            return record
    return None


def get_certificate(cert_id: str):
    for cert in load_certificates():
        if cert["cert_id"] == cert_id:
            return cert
    return None


def build_calculation_result(start: str, end: str, containers: int) -> dict:
    p1 = PORTS[start]
    p2 = PORTS[end]
    base_distance = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
    road_distance = estimate_route_distance(base_distance, "road")
    sea_distance = estimate_route_distance(base_distance, "sea")

    road_condition = traffic_service.summarize_traffic()
    ship_schedule = schedule_service.get_ship_schedule(p1["code"], p2["name"])

    road_carbon = EMISSION_FACTORS["road"] * road_distance * containers
    sea_carbon = (
        EMISSION_FACTORS["sea"] * sea_distance * containers
        + PORT_HANDLING_EMISSION_PER_CONTAINER * containers * 2
    )

    road_freight = TRANSPORT_COST_RATES["road"] * road_distance * containers
    sea_freight = TRANSPORT_COST_RATES["sea"] * sea_distance * containers

    road_time = calculate_financing_time_cost(road_distance, "road", containers)
    sea_time = calculate_financing_time_cost(sea_distance, "sea", containers)

    road_social = SOCIAL_COST_RATES["road"] * road_distance * containers
    sea_social = SOCIAL_COST_RATES["sea"] * sea_distance * containers

    road_risk = RISK_COST_RATES["road"] * road_distance * containers
    sea_risk = RISK_COST_RATES["sea"] * sea_distance * containers

    road_carbon_externality = road_carbon * SOCIAL_COST_OF_CARBON
    sea_carbon_externality = sea_carbon * SOCIAL_COST_OF_CARBON

    road_total = road_freight + road_time + road_social + road_risk + road_carbon_externality
    sea_total = sea_freight + sea_time + sea_social + sea_risk + sea_carbon_externality

    if sea_total < road_total:
        best_mode = "海運"
        social_savings = road_total - sea_total
    else:
        best_mode = "公路"
        social_savings = sea_total - road_total

    if best_mode == "海運":
        carbon_improvement = road_carbon - sea_carbon
        baseline = road_carbon
    else:
        carbon_improvement = sea_carbon - road_carbon
        baseline = sea_carbon

    reduction_pct = (carbon_improvement / baseline * 100) if baseline > 0 else 0
    dispatch = smart_dispatch(containers, road_condition, ship_schedule)
    optimization = compare_modes(base_distance, containers)
    optimal_ratio = calculate_optimal_transfer_ratio(base_distance, containers)

    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start": p1["name"],
        "end": p2["name"],
        "containers": containers,
        "base_distance": round(base_distance, 2),
        "road_distance": round(road_distance, 2),
        "sea_distance": round(sea_distance, 2),
        "road_carbon": round(road_carbon, 2),
        "sea_carbon": round(sea_carbon, 2),
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "best_mode": best_mode,
        "social_savings": round(social_savings),
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
        "start_name": p1["name"],
        "end_name": p2["name"],
        "start_lat": p1["lat"],
        "start_lon": p1["lon"],
        "end_lat": p2["lat"],
        "end_lon": p2["lon"],
        "road": {
            "freight": round(road_freight),
            "time": round(road_time),
            "social": round(road_social),
            "risk": round(road_risk),
            "carbon": round(road_carbon, 2),
            "carbon_externality": round(road_carbon_externality),
            "total": round(road_total),
        },
        "sea": {
            "freight": round(sea_freight),
            "time": round(sea_time),
            "social": round(sea_social),
            "risk": round(sea_risk),
            "carbon": round(sea_carbon, 2),
            "carbon_externality": round(sea_carbon_externality),
            "total": round(sea_total),
        },
        "best_mode": best_mode,
        "social_savings": round(social_savings),
        "carbon_improvement": round(carbon_improvement, 2),
        "reduction_pct": round(reduction_pct, 1),
        "recommendation": f"選擇 {best_mode} 相較替代方案可減少 {carbon_improvement:.0f} kg CO2e，約 {reduction_pct:.1f}%",
        "road_condition": {
            "level": road_condition["level"],
            "level_text": "🟢 順暢" if road_condition["level"] == "low" else "🟡 車多" if road_condition["level"] == "medium" else "🔴 壅塞",
            "avg_speed": road_condition["avg_speed"],
        },
        "ship_schedule": ship_schedule,
        "dispatch": dispatch,
        "optimization": optimization,
        "optimal_transfer_ratio": optimal_ratio,
    }


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
    return jsonify(traffic_service.get_live_traffic_speed())


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")
    containers = data.get("containers")

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

    return jsonify(build_calculation_result(start, end, containers))


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
def download_certificate(cert_id: str, lang: str):
    certificate = get_certificate(cert_id)
    if not certificate:
        return jsonify({"error": "查無證書"}), 404

    lang = "en" if lang == "en" else "zh"
    pdf_buffer = build_certificate_pdf(certificate, lang=lang)
    filename = f"certificate_{cert_id}_{'english' if lang == 'en' else 'chinese'}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/verify/<cert_id>")
def verify_certificate(cert_id: str):
    certificate = get_certificate(cert_id)
    return render_template("verify.html", valid=bool(certificate), cert=certificate, app_title=APP_TITLE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
