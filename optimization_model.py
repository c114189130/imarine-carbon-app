from config import (
    EMISSION_FACTORS,
    TRANSPORT_COST_RATES,
    TIME_VALUE_PER_HOUR,
    ROAD_SPEED_KMH,
    SEA_SPEED_KMH,
)

VSL = 50_000_000
CARBON_PRICE = 0.3
ACCIDENT_RATE = {"road": 0.015, "sea": 0.0005}

def calculate_transport_cost(d, c, m): return TRANSPORT_COST_RATES[m] * d * c
def calculate_carbon_emission(d, c, m): return EMISSION_FACTORS[m] * d * c
def calculate_carbon_cost(d, c, m): return calculate_carbon_emission(d, c, m) * CARBON_PRICE
def calculate_accident_cost(d, c, m): return (d * c * ACCIDENT_RATE[m] / 1_000_000) * VSL
def calculate_time_cost(d, c, m): return (d / (ROAD_SPEED_KMH if m == "road" else SEA_SPEED_KMH)) * TIME_VALUE_PER_HOUR * c

def calculate_total_social_cost(d, c, m):
    parts = {
        "transport": round(calculate_transport_cost(d, c, m)),
        "carbon": round(calculate_carbon_cost(d, c, m)),
        "accident": round(calculate_accident_cost(d, c, m)),
        "time": round(calculate_time_cost(d, c, m)),
    }
    parts["total"] = round(sum(parts.values()))
    return parts

def compare_modes(d, c):
    road = calculate_total_social_cost(d, c, "road")
    sea = calculate_total_social_cost(d, c, "sea")
    savings = {k: round(road[k] - sea[k]) for k in road}
    vsl_saved = calculate_accident_cost(d, c, "road") - calculate_accident_cost(d, c, "sea")
    carbon_reduction = calculate_carbon_emission(d, c, "road") - calculate_carbon_emission(d, c, "sea")
    carbon_pct = (carbon_reduction / calculate_carbon_emission(d, c, "road") * 100) if d * c > 0 else 0
    return {
        "road": road, "sea": sea, "savings": savings,
        "carbon_reduction_kg": round(carbon_reduction, 2),
        "carbon_reduction_pct": round(carbon_pct, 1),
        "vsl_saved": round(vsl_saved),
        "deaths_reduced": round(vsl_saved / VSL, 6),
    }

def calculate_optimal_transfer_ratio(d, c):
    ratios = []
    for r in [0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
        sea_c = c * r
        road_c = c - sea_c
        total = calculate_total_social_cost(d, road_c, "road")["total"] + calculate_total_social_cost(d, sea_c, "sea")["total"]
        ratios.append({"sea_ratio": round(r * 100, 1), "total_cost": total, "sea_containers": round(sea_c), "road_containers": round(road_c)})
    best = min(ratios, key=lambda x: x["total_cost"])
    return {"best": best, "candidates": ratios}