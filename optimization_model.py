VSL = 50000000
CARBON_PRICE = 0.3
ACCIDENT_RATE = {"road": 0.015, "sea": 0.0005}
TRANSPORT_COST = {"road": 60, "sea": 24}
EMISSION_FACTORS = {"road": 0.06, "sea": 0.02}
TIME_VALUE = 57

def calculate_transport_cost(d, c, m): return TRANSPORT_COST[m] * d * c
def calculate_carbon_emission(d, c, m): return EMISSION_FACTORS[m] * d * c
def calculate_carbon_cost(d, c, m): return calculate_carbon_emission(d, c, m) * CARBON_PRICE
def calculate_accident_cost(d, c, m): return (d * c * ACCIDENT_RATE[m] / 1000000) * VSL
def calculate_time_cost(d, c, m): return (d / (60 if m == "road" else 46)) * TIME_VALUE * c

def calculate_total_social_cost(d, c, m):
    return {
        "transport": round(calculate_transport_cost(d, c, m)),
        "carbon": round(calculate_carbon_cost(d, c, m)),
        "accident": round(calculate_accident_cost(d, c, m)),
        "time": round(calculate_time_cost(d, c, m))
    }

def compare_modes(d, c):
    road = calculate_total_social_cost(d, c, "road")
    sea = calculate_total_social_cost(d, c, "sea")
    
    road_total = sum(road.values())
    sea_total = sum(sea.values())
    
    road["total"] = round(road_total)
    sea["total"] = round(sea_total)
    
    savings = {k: round(road.get(k, 0) - sea.get(k, 0)) for k in road.keys()}
    accident_saved = calculate_accident_cost(d, c, "road") - calculate_accident_cost(d, c, "sea")
    
    road_factor = EMISSION_FACTORS["road"]
    sea_factor = EMISSION_FACTORS["sea"]
    reduction_pct = ((road_factor - sea_factor) / road_factor) * 100 if road_factor > 0 else 0
    
    return {
        "road": road,
        "sea": sea,
        "savings": savings,
        "carbon_reduction_kg": round((road_factor - sea_factor) * d * c, 2),
        "carbon_reduction_pct": round(reduction_pct, 1),
        "vsl_saved": round(accident_saved),
        "deaths_reduced": round(accident_saved / VSL, 6)
    }

def calculate_optimal_transfer_ratio(d, c):
    ratios = []
    for r in [0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
        road_c = c * (1 - r)
        sea_c = c * r
        total = calculate_transport_cost(d, road_c, "road") + calculate_transport_cost(d, sea_c, "sea")
        ratios.append({"sea_ratio": r * 100, "total_cost": total, "sea_containers": round(sea_c), "road_containers": round(road_c)})
    return min(ratios, key=lambda x: x["total_cost"])