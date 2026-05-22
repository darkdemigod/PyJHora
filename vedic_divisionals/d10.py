
from .varga_math import VargaMath

class D10:
    def compute(self, lon):
        part = 30 / 10
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 10 + idx) % 12
        return base * 30 + (lon % part) * 10
