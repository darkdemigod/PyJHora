
import time

class RealtimeTransitEngine:
    def stream(self, callback, interval=5):
        while True:
            callback({"event": "tick", "timestamp": time.time()})
            time.sleep(interval)
