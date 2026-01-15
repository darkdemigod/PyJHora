
class SubDashas:
    def expand(self, maha):
        antar = []
        for m in maha:
            span = m["end"] - m["start"]
            for k in maha:
                antar.append({"maha": m["lord"], "antar": k["lord"], "len": span/9})
        return antar
