
from vedic_divisionals.varga_runtime import VargaRuntime

class VargaAssembler:
    def __init__(self):
        self.runtime = VargaRuntime()

    def assemble(self, planet_positions):
        return self.runtime.build(planet_positions)
