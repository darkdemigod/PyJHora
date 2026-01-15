
from .vimshottari_real import VimshottariReal
from .sub_dashas import SubDashas

class FullDashaEngine:
    def __init__(self):
        self.maha = VimshottariReal()
        self.sub = SubDashas()

    def build(self, start_lord, start_jd):
        maha = self.maha.build(start_lord, start_jd)
        antar = self.sub.expand(maha)
        return {"maha": maha, "antar": antar}
