
from .varga_math import VargaMath

class D9:
    def compute(self, lon):
        part = 30 / 9
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 9 + idx) % 12
        return base * 30 + (lon % part) * 9
