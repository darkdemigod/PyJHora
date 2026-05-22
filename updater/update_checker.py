
import time

class UpdateChecker:
    def check(self):
        return {"update_available": False, "checked_at": time.time()}
