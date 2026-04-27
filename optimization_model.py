from config import (
    EMISSION_FACTORS,
    TRANSPORT_COST_RATES,
    TIME_VALUE_PER_HOUR,
    ROAD_SPEED_KMH,
    SEA_SPEED_KMH,
)

VSL = 50_000_000
CARBON_PRICE = 0.3
ACCIDENT_RATE = {
    "road": 0.015,
    "sea": 0.0005,
}


def calculate_transport_cost(distance_km: float, containers: float, mode: str) -> float:
    return TRANSPORT_COST_RATES[mode] * distance_km * containers


def calculate_carbon_emission(distance_km: float, containers: float, mode: str) -> float:
    return EMISSION_FACTORS[mode] * distance_km * containers


def calculate_carbon_cost(distance_km: float, containers: float, mode: str) -> float:
    return calculate_carbon_emission(distance_km, containers, mode) * CARBON_PRICE


def calculate_accident_cost(distance_km: float, containers: float, mode: str) -> float:
    return (distance_km * containers * ACCIDENT_RATE[mode] / 1_000_000) * VSL


def calculate_time_cost(distance_km: float, containers: float, mode: str) -> float:
    speed = ROAD_SPEED_KMH if mode == "road" else SEA_SPEED_KMH
    return (distance_km / speed) * TIME_VALUE_PER_HOUR * containers


def calculate_total_social_cost(distance_km: float, containers: float, mode: str) -> dict:
    parts = {
        "transport": round(calculate_transport_cost(distance_km, containers, mode)),
        "carbon": round(calculate_carbon_cost(distance_km, containers, mode)),
        "accident": round(calculate_accident_cost(distance_km, containers, mode)),
        "time": round(calculate_time_cost(distance_km, containers, mode)),
    }
    parts["total"] = round(sum(parts.values()))
    return parts


def compare_modes(distance_km: float, containers: float) -> dict:
    road = calculate_total_social_cost(distance_km, containers, "road")
    sea = calculate_total_social_cost(distance_km, containers, "sea")
    savings = {key: round(road[key] - sea[key]) for key in road.keys()}
    vsl_saved = calculate_accident_cost(distance_km, containers, "road") - calculate_accident_cost(distance_km, containers, "sea")
    carbon_reduction_kg = calculate_carbon_emission(distance_km, containers, "road") - calculate_carbon_emission(distance_km, containers, "sea")
    carbon_reduction_pct = (carbon_reduction_kg / calculate_carbon_emission(distance_km, containers, "road") * 100) if containers > 0 and distance_km > 0 else 0

    return {
        "road": road,
        "sea": sea,
        "savings": savings,
        "carbon_reduction_kg": round(carbon_reduction_kg, 2),
        "carbon_reduction_pct": round(carbon_reduction_pct, 1),
        "vsl_saved": round(vsl_saved),
        "deaths_reduced": round(vsl_saved / VSL, 6),
    }


def calculate_optimal_transfer_ratio(distance_km: float, containers: float) -> dict:
    ratios = []
    for sea_ratio in [0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
        sea_containers = containers * sea_ratio
        road_containers = containers - sea_containers
        road_total = calculate_total_social_cost(distance_km, road_containers, "road")["total"]
        sea_total = calculate_total_social_cost(distance_km, sea_containers, "sea")["total"]
        total_cost = round(road_total + sea_total)
        ratios.append({
            "sea_ratio": round(sea_ratio * 100, 1),
            "road_ratio": round((1 - sea_ratio) * 100, 1),
            "total_cost": total_cost,
            "sea_containers": round(sea_containers),
            "road_containers": round(road_containers),
        })

    best = min(ratios, key=lambda item: item["total_cost"])
    return {
        "best": best,
        "candidates": ratios,
    }