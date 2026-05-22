
from .varga_math import VargaMath

class D24:
    def compute(self, lon):
        part = 30 / 24
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 24 + idx) % 12
        return base * 30 + (lon % part) * 24
