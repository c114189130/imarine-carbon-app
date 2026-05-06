import random
import math
from datetime import datetime


class AIPredictor:
    """AI 預測引擎：壅塞機率、事故機率、碳排放預測"""

    def __init__(self):
        # 模擬訓練好的權重
        self.congestion_weights = {
            "hour_peak": 0.4,
            "day_weekend": 0.2,
            "weather_rain": 0.3,
            "special_event": 0.1,
        }
        self.accident_weights = {
            "congestion": 0.5,
            "night_driving": 0.2,
            "road_condition": 0.3,
        }

    def predict_congestion(self, day_of_week=None, hour=None, weather="clear"):
        """預測壅塞機率 (0-1)"""
        if day_of_week is None:
            now = datetime.now()
            day_of_week = now.weekday()
            hour = now.hour

        score = 0.0

        # 尖峰時段
        if day_of_week < 5:  # 平日
            if 7 <= hour <= 9:   # 早尖峰
                score += 0.6
            elif 17 <= hour <= 19:  # 晚尖峰
                score += 0.7
            elif 10 <= hour <= 16:
                score += 0.2
            else:
                score += 0.05
        else:  # 假日
            if 10 <= hour <= 20:
                score += 0.4
            else:
                score += 0.1

        # 天氣影響
        if weather == "rain":
            score += 0.3
        elif weather == "typhoon":
            score += 0.6

        # 加入非線性轉換 (sigmoid-like)
        probability = 1 / (1 + math.exp(-(score - 0.3) * 8))
        probability = round(min(0.95, max(0.05, probability + random.uniform(-0.05, 0.05))), 3)

        level = "high" if probability > 0.7 else ("medium" if probability > 0.35 else "low")
        return {"probability": probability, "level": level}

    def predict_accident_risk(self, road_km, congestion_level, is_night=False):
        """預測事故機率"""
        base = ACCIDENT_RATE["road"] * (road_km / 100)

        # 壅塞加成
        if congestion_level == "high":
            base *= 2.5
        elif congestion_level == "medium":
            base *= 1.5

        # 夜間加成
        if is_night:
            base *= 1.8

        return round(min(0.01, base + random.uniform(-0.0001, 0.0001)), 6)

    def predict_carbon_savings(self, road_km, sea_km, containers_feu):
        """預測碳排節省"""
        road = EMISSION_FACTORS["road"] * road_km * containers_feu
        sea = EMISSION_FACTORS["sea"] * sea_km * containers_feu + PORT_HANDLING_EMISSION * containers_feu * 2
        return round(road - sea, 2)

    def predict_eta(self, distance_km, mode, congestion_level="medium"):
        """預測 ETA"""
        if mode == "road":
            delay = {"low": 1.0, "medium": 1.3, "high": 1.8}
            hours = (distance_km / ROAD_SPEED_KMH) * delay.get(congestion_level, 1.0)
        else:
            hours = distance_km / SEA_SPEED_KMH
        return round(hours, 1)


# 全域單例
ai_predictor = AIPredictor()