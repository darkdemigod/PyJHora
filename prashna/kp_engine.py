
class KPEngine:
    def decide(self, score):
        if score > 0: return "YES"
        if score < 0: return "NO"
        return "UNCERTAIN"
