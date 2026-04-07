"""
AI 最佳化引擎 - 多目標決策
支援：成本、碳排放、風險 三個維度的加權評分
"""

def normalize(value, max_value):
    if max_value is None or max_value == 0:
        return 0
    max_val = max_value if max_value > 0 else 1
    return min(1.0, value / max_val)

def get_max_values(road, sea):
    return {
        "cost": max(road["total"], sea["total"]),
        "carbon": max(road["carbon"], sea["carbon"]),
        "risk": max(road["vsl"], sea["vsl"])
    }

def recommend_v2(road, sea, weights):
    """
    AI 多目標決策推薦
    
    參數:
        road: 公路運輸數據 {total, carbon, vsl, ...}
        sea: 海運運輸數據 {total, carbon, vsl, ...}
        weights: 權重配置 {"cost": 0.4, "carbon": 0.4, "risk": 0.2}
    
    返回:
        (最佳模式, 最佳分數, 所有分數)
    """
    
    max_values = get_max_values(road, sea)
    
    road_score = (
        weights.get("cost", 0.4) * normalize(road["total"], max_values["cost"]) +
        weights.get("carbon", 0.4) * normalize(road["carbon"], max_values["carbon"]) +
        weights.get("risk", 0.2) * normalize(road["vsl"], max_values["risk"])
    )
    
    sea_score = (
        weights.get("cost", 0.4) * normalize(sea["total"], max_values["cost"]) +
        weights.get("carbon", 0.4) * normalize(sea["carbon"], max_values["carbon"]) +
        weights.get("risk", 0.2) * normalize(sea["vsl"], max_values["risk"])
    )
    
    if sea_score < road_score:
        best_mode = "海運"
        best_score = round(sea_score, 4)
    else:
        best_mode = "公路"
        best_score = round(road_score, 4)
    
    all_scores = {
        "road": round(road_score, 4),
        "sea": round(sea_score, 4)
    }
    
    return best_mode, best_score, all_scores

def explain_decision(road, sea, weights):
    best_mode, best_score, scores = recommend_v2(road, sea, weights)
    
    explanation = f"""
    🤖 AI 決策分析報告
    ====================
    公路綜合分數：{scores['road']}
    海運綜合分數：{scores['sea']}
    
    權重配置：
    - 成本權重：{weights.get('cost', 0.4) * 100}%
    - 碳排權重：{weights.get('carbon', 0.4) * 100}%
    - 風險權重：{weights.get('risk', 0.2) * 100}%
    
    推薦方案：{best_mode}
    """
    
    return explanation

# 不同場景的推薦權重
SCENE_WEIGHTS = {
    "default": {"cost": 0.4, "carbon": 0.4, "risk": 0.2},
    "cost_sensitive": {"cost": 0.7, "carbon": 0.2, "risk": 0.1},
    "green_first": {"cost": 0.2, "carbon": 0.7, "risk": 0.1},
    "balanced": {"cost": 0.33, "carbon": 0.34, "risk": 0.33},
    "risk_averse": {"cost": 0.3, "carbon": 0.2, "risk": 0.5}
}

if __name__ == "__main__":
    test_road = {"total": 15000, "carbon": 420, "vsl": 238}
    test_sea = {"total": 5000, "carbon": 140, "vsl": 31.5}
    
    best, score, scores = recommend_v2(test_road, test_sea, SCENE_WEIGHTS["default"])
    print(f"最佳方案：{best}")
    print(f"公路分數：{scores['road']}")
    print(f"海運分數：{scores['sea']}")