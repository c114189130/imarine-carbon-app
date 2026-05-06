"""
ESG 碳排管理模組
"""

CARBON_PRICE = 0.3
VSL = 50_000_000


def get_esg_report(road_emission: float, sea_emission: float, containers: int, distance_km: float) -> dict:
    carbon_saved = road_emission - sea_emission
    carbon_pct = (carbon_saved / road_emission * 100) if road_emission > 0 else 0
    carbon_credit_value = carbon_saved * CARBON_PRICE
    
    return {
        "road_emission": round(road_emission, 2),
        "sea_emission": round(sea_emission, 2),
        "carbon_saved": round(carbon_saved, 2),
        "carbon_reduction_pct": round(carbon_pct, 1),
        "carbon_credit_value": round(carbon_credit_value, 2),
        "trees_planted": int(carbon_saved / 22),
    }