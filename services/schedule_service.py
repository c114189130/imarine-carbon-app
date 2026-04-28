import json
from pathlib import Path
from datetime import datetime
from config import SCHEDULE_FILE, DEFAULT_SCHEDULE


class ScheduleService:
    def __init__(self):
        self.schedule = self._load_schedule()

    def _load_schedule(self):
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return DEFAULT_SCHEDULE
        return DEFAULT_SCHEDULE

    def get_ship_schedule(self, start_code, end_name, ship_date=""):
        port_data = self.schedule.get(start_code, {"ships": []})
        matching_ships = []
        
        for ship in port_data.get("ships", []):
            if ship.get("destination") == end_name:
                matching_ships.append(ship)
        
        if matching_ships:
            selected_ship = matching_ships[0]
            if ship_date:
                try:
                    target_date = datetime.strptime(ship_date, "%Y-%m-%d")
                    for ship in matching_ships:
                        try:
                            etd_str = ship.get("etd", "")
                            etd_parts = etd_str.split(" ")
                            if len(etd_parts) == 2:
                                etd_date = datetime.strptime(f"2026/{etd_parts[0]} {etd_parts[1]}", "%Y/%m/%d %H:%M")
                                if etd_date >= target_date:
                                    selected_ship = ship
                                    break
                        except:
                            pass
                except:
                    pass
            
            ship = selected_ship
            return {
                "name": ship.get("name", "N/A"),
                "name_zh": ship.get("name_zh", ""),
                "voyage": ship.get("voyage", ""),
                "route": ship.get("route", "TBS"),
                "etd": ship.get("etd", "待確認"),
                "eta": ship.get("eta", "待確認"),
                "hours": ship.get("hours", 24),
                "available": ship.get("available", 0),
                "capacity": ship.get("capacity", 500),
                "destination": ship.get("destination", end_name),
                "dest_code": ship.get("dest_code", ""),
                "schedule_day": ship.get("schedule_day", ""),
                "is_virtual": "虛擬" in ship.get("name_zh", ""),
                "all_ships": matching_ships
            }
        
        return {
            "name": "待確認",
            "name_zh": "",
            "voyage": "",
            "route": "TBS",
            "etd": "待確認",
            "eta": "待確認",
            "hours": 24,
            "available": 0,
            "capacity": 500,
            "destination": end_name,
            "dest_code": "",
            "schedule_day": "",
            "is_virtual": True,
            "all_ships": []
        }