from config import CARGO_TYPES


class DecisionEngine:
    """多因子決策引擎"""

    def evaluate(self, cargo_type, road_data, ship_data, time_estimation, cf):
        reasons = []
        scores = {"sea": 0, "road": 0}

        cargo = CARGO_TYPES.get(cargo_type, CARGO_TYPES["normal"])

        # 1. 貨物類型
        if cargo_type == "dangerous":
            scores["sea"] += 40
            reasons.append("🛑 危險品優先海運（安全考量）")
        elif cargo_type == "cold_chain":
            scores["sea"] += 20
            reasons.append("❄️ 冷鏈貨物建議海運（穩定環境）")

        # 2. 能否趕船
        if ship_data.get("can_catch", False):
            scores["sea"] += 30
            reasons.append("✅ 貨物可趕上最近船班")
        else:
            scores["road"] += 35
            reasons.append("⏰ 貨物無法趕上船班，建議陸拖")

        # 3. 時間比較
        sea_time = time_estimation.get("sea_time", 99)
        road_time = time_estimation.get("road_time", 99)
        if sea_time < road_time:
            scores["sea"] += 15
            reasons.append(f"⏱ 海運較快（{sea_time}h vs {road_time}h）")
        elif road_time < sea_time * 0.7:
            scores["road"] += 15
            reasons.append(f"⏱ 陸拖明顯較快（{road_time}h vs {sea_time}h）")

        # 4. 壅塞
        if road_data.get("level") == "high":
            scores["sea"] += 20
            reasons.append("🚦 公路壅塞，海運優勢明顯")

        # 5. 成本
        if ship_data.get("cost_savings", 0) > 0:
            scores["sea"] += 10
            reasons.append(f"💰 海運節省 NT$ {ship_data['cost_savings']:,.0f}")

        # 6. ESG
        scores["sea"] += 10
        reasons.append("🌱 海運碳排放僅公路 1/3")

        if scores["sea"] >= scores["road"]:
            mode = "sea"
        else:
            mode = "road"

        total = scores["sea"] + scores["road"]
        confidence = round(max(scores["sea"], scores["road"]) / total * 100, 1) if total > 0 else 50

        return {
            "mode": mode,
            "confidence": confidence,
            "scores": scores,
            "reasons": reasons,
        }


decision_engine = DecisionEngine()