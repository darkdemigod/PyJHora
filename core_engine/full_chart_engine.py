
from core_engine.chart_builder_real import ChartBuilderReal
from core_engine.varga_assembler import VargaAssembler
from dasha_core.full_dasha_engine import FullDashaEngine

class FullChartEngine:
    def __init__(self):
        self.builder = ChartBuilderReal()
        self.vargas = VargaAssembler()
        self.dasha = FullDashaEngine()

    def build_all(self, jd, lat, lon, planet_ids, dasha_lord=None):
        base = self.builder.build(jd, lat, lon, planet_ids)
        base["vargas"] = self.vargas.assemble(base["planets"])
        if dasha_lord:
            base["dasha"] = self.dasha.build(dasha_lord, jd)
        return base
