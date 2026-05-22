
from .varga_math import VargaMath

class D30:
    def compute(self, lon):
        part = 30 / 30
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 30 + idx) % 12
        return base * 30 + (lon % part) * 30
