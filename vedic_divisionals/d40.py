
from .varga_math import VargaMath

class D40:
    def compute(self, lon):
        part = 30 / 40
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 40 + idx) % 12
        return base * 30 + (lon % part) * 40
