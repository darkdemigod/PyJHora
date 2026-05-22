
from vedic_divisionals.d1 import D1
from vedic_divisionals.d2 import D2
from vedic_divisionals.d3 import D3
from vedic_divisionals.d4 import D4
from vedic_divisionals.d7 import D7
from vedic_divisionals.d9 import D9
from vedic_divisionals.d10 import D10
from vedic_divisionals.d12 import D12
from vedic_divisionals.d16 import D16
from vedic_divisionals.d20 import D20
from vedic_divisionals.d24 import D24
from vedic_divisionals.d27 import D27
from vedic_divisionals.d30 import D30
from vedic_divisionals.d40 import D40
from vedic_divisionals.d45 import D45
from vedic_divisionals.d60 import D60

class VargaRuntime:
    def __init__(self):
        self.maps = {
            "D1": D1(), "D2": D2(), "D3": D3(), "D4": D4(),
            "D7": D7(), "D9": D9(), "D10": D10(), "D12": D12(),
            "D16": D16(), "D20": D20(), "D24": D24(), "D27": D27(),
            "D30": D30(), "D40": D40(), "D45": D45(), "D60": D60()
        }

    def build(self, positions):
        out = {}
        for name, engine in self.maps.items():
            out[name] = {}
            for p, d in positions.items():
                out[name][p] = engine.compute(d["longitude"])
        return out
