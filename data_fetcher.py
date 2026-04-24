import requests
from datetime import datetime

def get_sea_route(start_port, end_port):
    try:
        mock_routes = {("kaohsiung", "taichung"): {"distance": 190, "time": 8, "congestion": 0.2, "fuel_cost": 8500}, ("kaohsiung", "keelung"): {"distance": 380, "time": 16, "congestion": 0.3, "fuel_cost": 17000}, ("kaohsiung", "taipei"): {"distance": 360, "time": 15, "congestion": 0.25, "fuel_cost": 16000}, ("kaohsiung", "hualien"): {"distance": 280, "time": 12, "congestion": 0.15, "fuel_cost": 12500}, ("taichung", "kaohsiung"): {"distance": 190, "time": 8, "congestion": 0.2, "fuel_cost": 8500}, ("taichung", "keelung"): {"distance": 200, "time": 9, "congestion": 0.25, "fuel_cost": 9000}, ("keelung", "kaohsiung"): {"distance": 380, "time": 16, "congestion": 0.3, "fuel_cost": 17000}}
        return mock_routes.get((start_port, end_port), {"distance": 250, "time": 11, "congestion": 0.2, "fuel_cost": 11000})
    except Exception as e:
        return {"distance": 250, "time": 11, "congestion": 0.2, "fuel_cost": 11000}

def get_road_data(start_port, end_port):
    try:
        return {"distance": 250, "time": 4.2, "congestion": 0.6, "toll_cost": 300, "fuel_cost": 875}
    except Exception as e:
        return {"distance": 250, "time": 4.2, "congestion": 0.6, "toll_cost": 300, "fuel_cost": 875}

def get_fuel_prices():
    return {"bunker_fuel": 620, "diesel": 32.5, "gasoline": 30.8, "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": "台灣中油參考價格"}

def get_port_capacity(port_code):
    capacities = {"KHH": 10400000, "TXG": 1800000, "KEL": 1600000, "TPE": 1800000, "HUN": 800000}
    return {"port_code": port_code, "annual_teu": capacities.get(port_code, 1000000), "growth_rate": 0.03, "last_update": "2023"}