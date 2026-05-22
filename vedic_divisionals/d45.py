
from .varga_math import VargaMath

class D45:
    def compute(self, lon):
        part = 30 / 45
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 45 + idx) % 12
        return base * 30 + (lon % part) * 45
