"""
Bridge: Lahiri ayanamsha via pyswisseph
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


class TrueLahiri:
    def offset(self, jd):
        """Return Lahiri ayanamsha for given Julian Day."""
        try:
            if _HAS_SWE:
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                return swe.get_ayanamsa_ut(jd)
        except Exception:
            pass
        return 23.85  # approximate modern value
