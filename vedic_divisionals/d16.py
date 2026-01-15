
from .varga_math import VargaMath

class D16:
    def compute(self, lon):
        part = 30 / 16
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 16 + idx) % 12
        return base * 30 + (lon % part) * 16
