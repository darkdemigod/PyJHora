
from .varga_math import VargaMath

class D7:
    def compute(self, lon):
        part = 30 / 7
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 7 + idx) % 12
        return base * 30 + (lon % part) * 7
