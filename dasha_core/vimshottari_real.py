
class VimshottariReal:
    PERIODS = {
        "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10,
        "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
    }
    ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]

    def build(self, start_lord, start_jd):
        idx = self.ORDER.index(start_lord)
        timeline = []
        jd = start_jd
        for i in range(len(self.ORDER)):
            lord = self.ORDER[(idx + i) % len(self.ORDER)]
            years = self.PERIODS[lord]
            timeline.append({"lord": lord, "start": jd, "end": jd + years * 365.25})
            jd += years * 365.25
        return timeline
