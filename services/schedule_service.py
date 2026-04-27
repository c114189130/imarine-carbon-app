import json
from pathlib import Path
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

    def get_ship_schedule(self, start_code: str, end_name: str) -> dict:
        port_data = self.schedule.get(start_code, {"ships": []})
        for ship in port_data.get("ships", []):
            if ship.get("destination") == end_name:
                return ship
        return {
            "name": "Evergreen TBS",
            "eta_hours": 24,
            "available": 150,
            "destination": end_name,
            "route": "TBS",
            "eta": "THU",
        }