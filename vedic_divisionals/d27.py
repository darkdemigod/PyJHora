
from .varga_math import VargaMath

class D27:
    def compute(self, lon):
        part = 30 / 27
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 27 + idx) % 12
        return base * 30 + (lon % part) * 27
