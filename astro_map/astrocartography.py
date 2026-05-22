
class AstroCartography:
    def project(self, positions):
        return {p: [(0, d["longitude"])] for p, d in positions.items()}
