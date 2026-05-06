import random


class ShipBookingSystem:
    def __init__(self):
        self.ships = {}

    def _key(self, start, end):
        return f"{start}-{end}"

    def init_route(self, start, end, total_feu=809):
        key = self._key(start, end)
        if key not in self.ships:
            self.ships[key] = {"total": total_feu, "remaining": random.randint(50, total_feu)}

    def get_remaining(self, start, end):
        key = self._key(start, end)
        self.init_route(start, end)
        return self.ships[key]["remaining"]

    def book(self, start, end, amount):
        key = self._key(start, end)
        self.init_route(start, end)
        ship = self.ships[key]
        if ship["remaining"] >= amount:
            ship["remaining"] -= amount
            return True, f"訂位成功！剩餘 {ship['remaining']} FEU"
        return False, f"艙位不足（剩餘 {ship['remaining']} FEU，需求 {amount} FEU）"

    def is_available(self, start, end, amount):
        return self.get_remaining(start, end) >= amount


booking_system = ShipBookingSystem()