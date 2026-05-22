"""
Bridge module: connects ASTRO_OS to JHora's Swiss Ephemeris via pyswisseph
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import swisseph as swe
    _HAS_SWE = True
    _ephe_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'jhora', 'data', 'ephe')
    swe.set_ephe_path(_ephe_path)
except ImportError:
    _HAS_SWE = False

PLANET_IDS = {
    "Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2,
    "Jupiter": 5, "Venus": 3, "Saturn": 6,
    "Rahu": 11, "Ketu": 11
}

class SwissReal:
    def planet(self, jd, pid):
        """Return sidereal planet data dict for given Julian Day and planet id."""
        try:
            if _HAS_SWE:
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
                result, _ = swe.calc_ut(jd, pid, flags)
                lon = result[0] % 360
                # Ketu is always 180° from Rahu
                if pid == 11:
                    result2, _ = swe.calc_ut(jd, 11, flags)
                    lon = (result2[0] + 180) % 360
                return {
                    "longitude": lon,
                    "latitude": result[1],
                    "distance": result[2],
                    "speed": result[3],
                    "retrograde": result[3] < 0
                }
        except Exception:
            pass
        # Fallback: return a zero-filled dict
        return {"longitude": 0.0, "latitude": 0.0, "distance": 1.0, "speed": 0.0, "retrograde": False}
