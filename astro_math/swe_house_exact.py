"""
Bridge: house cusp calculations via pyswisseph
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


class SwissHouseExact:
    def compute(self, jd, lat, lon, system=b'P'):
        """Compute Placidus house cusps and ascmc. Returns (cusps_list, ascmc_dict)."""
        try:
            if _HAS_SWE:
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                cusps, ascmc = swe.houses(jd, lat, lon, system)
                ayanamsha = swe.get_ayanamsa_ut(jd)
                sid_cusps = [(c - ayanamsha) % 360 for c in cusps[1:]]
                sid_asc = (ascmc[0] - ayanamsha) % 360
                sid_mc  = (ascmc[1] - ayanamsha) % 360
                return sid_cusps, {
                    "ascendant": sid_asc,
                    "mc": sid_mc,
                    "armc": ascmc[2],
                    "vertex": ascmc[3]
                }
        except Exception:
            pass
        # Fallback
        cusps = [i * 30.0 for i in range(12)]
        return cusps, {"ascendant": 0.0, "mc": 270.0, "armc": 0.0, "vertex": 0.0}
