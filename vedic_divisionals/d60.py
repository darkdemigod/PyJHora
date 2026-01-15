
from .varga_math import VargaMath

class D60:
    def compute(self, lon):
        part = 30 / 60
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 60 + idx) % 12
        return base * 30 + (lon % part) * 60
