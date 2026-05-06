import random

class ShipBookingSystem:
    def __init__(self):
        self.ships = {
            "KHH-TXG": {"name": "高雄→台中", "total": 809, "remaining": 809},
            "KHH-TPE": {"name": "高雄→台北", "total": 809, "remaining": 809},
            "TXG-TPE": {"name": "台中→台北", "total": 809, "remaining": 809},
            "TPE-KHH": {"name": "台北→高雄", "total": 809, "remaining": 809},
            "TPE-TXG": {"name": "台北→台中", "total": 809, "remaining": 809},
        }

    def get_remaining(self, route_key):
        """取得剩餘艙位"""
        ship = self.ships.get(route_key, {"remaining": 0})
        return ship["remaining"]

    def book(self, route_key, amount):
        """訂艙位，回傳 True/False"""
        if route_key not in self.ships:
            return False, "無此航線"
        ship = self.ships[route_key]
        if ship["remaining"] >= amount:
            ship["remaining"] -= amount
            return True, f"訂位成功，剩餘 {ship['remaining']} FEU"
        return False, f"艙位不足（剩餘 {ship['remaining']} FEU，需求 {amount} FEU）"

    def reset_random(self):
        """隨機重置艙位（模擬新船班）"""
        for key in self.ships:
            self.ships[key]["remaining"] = random.randint(
                int(self.ships[key]["total"] * 0.1),
                int(self.ships[key]["total"] * 0.9)
            )

# 全域單例
booking_system = ShipBookingSystem()