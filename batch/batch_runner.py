
class BatchRunner:
    def run(self, start, end, step):
        out = []
        jd = start
        while jd <= end:
            out.append(jd)
            jd += step
        return out
