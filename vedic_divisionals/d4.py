
from .varga_math import VargaMath

class D4:
    def compute(self, lon):
        part = 30 / 4
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 4 + idx) % 12
        return base * 30 + (lon % part) * 4
