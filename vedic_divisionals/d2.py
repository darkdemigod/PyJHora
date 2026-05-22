
from .varga_math import VargaMath

class D2:
    def compute(self, lon):
        part = 30 / 2
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 2 + idx) % 12
        return base * 30 + (lon % part) * 2
