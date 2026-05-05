import json
from pathlib import Path
from datetime import datetime
from config import SCHEDULE_FILE, DEFAULT_SHIPS

class ScheduleService:
    def __init__(self):
        self.schedule = self._load()
    
    def _load(self):
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return DEFAULT_SHIPS
    
    def get_ship_schedules(self, start_code, end_name, containers_feu, ship_date=""):
        """取得匹配船班列表，含多個航次"""
        port_data = self.schedule.get(start_code, {"ships": []})
        matched = []
        for ship in port_data.get("ships", []):
            if ship.get("destination") == end_name or ship.get("dest_code") == end_name:
                # 檢查所有航次
                sailings = ship.get("next_sailings", [])
                for s in sailings:
                    if s.get("available_feu", 0) >= containers_feu:
                        matched.append({
                            "ship_name": f"{ship['name']}({ship['name_zh']})",
                            "voyage": ship["voyage"],
                            "route": ship["route"],
                            "etd": s["etd"],
                            "eta": s["eta"],
                            "available_feu": s["available_feu"],
                            "capacity_feu": ship["capacity_feu"],
                            "capacity_teu": ship["capacity_teu"],
                            "hours": ship["hours"],
                            "schedule_day": ship["schedule_day"],
                            "destination": ship["destination"]
                        })
        # 如果沒匹配，回傳預設
        if not matched:
            matched = [{
                "ship_name": "待確認航班",
                "voyage": "-",
                "route": "-",
                "etd": "待確認",
                "eta": "待確認",
                "available_feu": 0,
                "capacity_feu": 0,
                "capacity_teu": 0,
                "hours": 0,
                "schedule_day": "-",
                "destination": end_name
            }]
        return matched