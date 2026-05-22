
from .varga_math import VargaMath

class D3:
    def compute(self, lon):
        part = 30 / 3
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 3 + idx) % 12
        return base * 30 + (lon % part) * 3
