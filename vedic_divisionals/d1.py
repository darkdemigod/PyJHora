
from .varga_math import VargaMath

class D1:
    def compute(self, lon):
        part = 30 / 1
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 1 + idx) % 12
        return base * 30 + (lon % part) * 1
