
from realtime.transit_engine import RealtimeTransitEngine

class RealtimeLinker:
    def __init__(self):
        self.engine = RealtimeTransitEngine()

    def start(self, callback):
        self.engine.stream(callback)
