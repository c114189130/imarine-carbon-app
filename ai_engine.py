def normalize(value, max_value):
    if max_value is None or max_value == 0:
        return 0
    return min(1.0, value / max_value if max_value > 0 else 0)

def get_max_values(road, sea):
    return {"cost": max(road["total"], sea["total"]), "carbon": max(road["carbon"], sea["carbon"]), "risk": max(road["vsl"], sea["vsl"])}

def recommend_v2(road, sea, weights):
    max_values = get_max_values(road, sea)
    road_score = weights.get("cost", 0.4) * normalize(road["total"], max_values["cost"]) + weights.get("carbon", 0.4) * normalize(road["carbon"], max_values["carbon"]) + weights.get("risk", 0.2) * normalize(road["vsl"], max_values["risk"])
    sea_score = weights.get("cost", 0.4) * normalize(sea["total"], max_values["cost"]) + weights.get("carbon", 0.4) * normalize(sea["carbon"], max_values["carbon"]) + weights.get("risk", 0.2) * normalize(sea["vsl"], max_values["risk"])
    best_mode = "海運" if sea_score < road_score else "公路"
    return best_mode, round(min(sea_score, road_score), 4), {"road": round(road_score, 4), "sea": round(sea_score, 4)}

SCENE_WEIGHTS = {"default": {"cost": 0.4, "carbon": 0.4, "risk": 0.2}, "cost_sensitive": {"cost": 0.7, "carbon": 0.2, "risk": 0.1}, "green_first": {"cost": 0.2, "carbon": 0.7, "risk": 0.1}, "balanced": {"cost": 0.33, "carbon": 0.34, "risk": 0.33}, "risk_averse": {"cost": 0.3, "carbon": 0.2, "risk": 0.5}}