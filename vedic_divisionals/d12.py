
from .varga_math import VargaMath

class D12:
    def compute(self, lon):
        part = 30 / 12
        idx = int((lon % 30) // part)
        base = (VargaMath.sign_index(lon) * 12 + idx) % 12
        return base * 30 + (lon % part) * 12
