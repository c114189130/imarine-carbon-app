import random

class TDXAPI:
    def __init__(self):
        pass

    def get_live_traffic_speed(self):
        road_ids = ["NH1-S-0", "NH1-S-1", "NH1-S-2", "NH1-S-3", "NH1-S-4"]
        return [{"id": rid, "speed": random.randint(20, 90)} for rid in road_ids]

def get_live_traffic_speed():
    api = TDXAPI()
    return api.get_live_traffic_speed()