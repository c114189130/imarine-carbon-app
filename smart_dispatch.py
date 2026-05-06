from ai_predict import estimate_transport_time

def smart_dispatch(containers, distance_km, road_data, ship_data, cargo_type="normal"):
    """
    智慧派遣決策引擎 v2
    回傳: { mode, reason, time_estimation, score }
    """
    time_est = estimate_transport_time(
        distance_km,
        road_data.get("avg_speed", 60),
        road_data.get("level", "medium"),
        ship_data
    )

    decision = {"time_estimation": time_est}
    reasons = []

    # 1. 特殊貨（危險品）→ 海運
    if cargo_type == "special":
        decision["mode"] = "sea"
        decision["score"] = 95
        reasons.append("🛑 危險品/特殊貨物優先海運")
        decision["reasons"] = reasons
        return decision

    # 2. 時效判斷：海運來不及 → 公路
    if time_est["sea_time"] > time_est["road_time"] * 1.5:
        decision["mode"] = "road"
        decision["score"] = 80
        reasons.append(f"⏱ 海運需 {time_est['sea_time']}h，公路僅 {time_est['road_time']}h，海運來不及")
        decision["reasons"] = reasons
        return decision

    # 3. 公路壅塞 → 海運
    if road_data.get("level") == "high":
        decision["mode"] = "sea"
        decision["score"] = 90
        reasons.append(f"🚦 公路壅塞（{road_data.get('avg_speed', '?')} km/h），轉海運")
        decision["reasons"] = reasons
        return decision

    # 4. 船快到了 → 海運
    if ship_data.get("next_ship_hours", 99) <= 12:
        decision["mode"] = "sea"
        decision["score"] = 85
        reasons.append(f"🚢 船班 {ship_data.get('next_ship_hours')}h 內開航，建議海運")
        decision["reasons"] = reasons
        return decision

    # 5. 船班剛過 → 公路
    if ship_data.get("next_ship_hours", 0) >= 48:
        decision["mode"] = "road"
        decision["score"] = 75
        reasons.append(f"⏳ 最近船班需等 {ship_data.get('next_ship_hours')}h，建議公路")
        decision["reasons"] = reasons
        return decision

    # 6. 預設：海運（藍色公路優先）
    decision["mode"] = "sea"
    decision["score"] = 70
    reasons.append("🌊 綜合評估：藍色公路為最佳選擇")
    decision["reasons"] = reasons
    return decision