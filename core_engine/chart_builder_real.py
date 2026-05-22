
from astro_math.swe_real_bindings import SwissReal
from astro_math.swe_house_exact import SwissHouseExact
from vedic_core.lahiri_true import TrueLahiri

class ChartBuilderReal:
    def __init__(self):
        self.swe = SwissReal()
        self.houses = SwissHouseExact()
        self.lahiri = TrueLahiri()

    def build(self, jd, lat, lon, planet_ids):
        planets = {}
        for name, pid in planet_ids.items():
            planets[name] = self.swe.planet(jd, pid)

        houses, ascmc = self.houses.compute(jd, lat, lon)
        ayanamsha = self.lahiri.offset(jd)

        return {
            "planets": planets,
            "houses": houses,
            "ascmc": ascmc,
            "ayanamsha": ayanamsha
        }
