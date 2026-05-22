"""
Vedic V4.0 Prediction Engine
Integrates Vimshottari Dasha, Marriage Timing, Mangal Dosha, and Yoga detection.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from jhora import utils, const
from jhora.panchanga import drik
from jhora.horoscope.chart import charts, yoga as yoga_module, dosha as dosha_module
from jhora.horoscope.dhasa.graha import vimsottari

PLANET_NAMES_LIST = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu", "Lagna"
]

NAK_LORDS = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
]

DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10,
    "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

DASHA_ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]

MARRIAGE_LORDS = {"Venus", "Jupiter", "Moon"}
MANGAL_HOUSES  = {1, 2, 4, 7, 8, 12}

RASI_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def _jd_to_date_str(jd):
    try:
        g = utils.jd_to_gregorian(jd)
        return f"{int(g[2]):02d}-{int(g[1]):02d}-{int(g[0])}"
    except Exception:
        return "N/A"

def _pname(pid):
    if isinstance(utils.PLANET_NAMES, dict):
        return utils.PLANET_NAMES.get(pid, PLANET_NAMES_LIST[pid] if pid < len(PLANET_NAMES_LIST) else f"P{pid}")
    try:
        return PLANET_NAMES_LIST[pid]
    except Exception:
        return f"P{pid}"


class VedicV4Predictor:
    def predict(self, jd, place):
        result = {}

        # ── Planet positions ─────────────────────────────────────
        planet_positions = []
        try:
            raw = charts.rasi_chart(jd, place)
            for entry in raw:
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    pid, pos = entry
                    if isinstance(pos, (list, tuple)) and len(pos) == 2:
                        rasi_idx, lon_in_rasi = pos
                    else:
                        rasi_idx, lon_in_rasi = 0, _safe_float(pos)
                    planet_positions.append({
                        "id": pid,
                        "name": _pname(pid),
                        "rasi": rasi_idx,
                        "house": rasi_idx + 1,
                        "longitude": rasi_idx * 30.0 + _safe_float(lon_in_rasi)
                    })
        except Exception as e:
            result["planet_error"] = str(e)

        # ── Vimshottari Dasha ────────────────────────────────────
        try:
            nakshatra_info = drik.nakshatra(jd, place)
            n_idx = int(nakshatra_info[0]) if isinstance(nakshatra_info, (list, tuple)) else 1
            start_lord = NAK_LORDS[(n_idx - 1) % 27]
            result["dasha_lord"] = start_lord

            # get_vimsottari_dhasa_bhukthi returns (start_info, periods_list)
            # periods_list items: [maha_lord_id, antar_lord_id, start_date_str]
            raw = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)
            if isinstance(raw, (list, tuple)) and len(raw) == 2 and isinstance(raw[1], list):
                _si, periods_list = raw
            else:
                periods_list = list(raw) if raw else []

            dasha_list = []
            seen_maha  = set()
            for period in periods_list:
                try:
                    maha_id = period[0]
                    if maha_id in seen_maha:
                        continue
                    seen_maha.add(maha_id)
                    start_dt = str(period[2]) if len(period) > 2 else "N/A"
                    dasha_list.append({
                        "planet":     _pname(maha_id),
                        "start_date": start_dt,
                    })
                except Exception:
                    continue
            result["vimshottari_dasha"] = {"start_lord": start_lord, "periods": dasha_list[:9]}
        except Exception as e:
            result["dasha_error"] = str(e)

        # ── Marriage Timing ──────────────────────────────────────
        try:
            marriage_lords_present = []
            for p in planet_positions:
                if p["name"] in MARRIAGE_LORDS:
                    marriage_lords_present.append(f"{p['name']} in house {p['house']}")

            marriage_houses = [p for p in planet_positions if p["house"] in {7, 2}]
            result["marriage_timing"] = {
                "marriage_lords":  marriage_lords_present,
                "seventh_house":   [p["name"] for p in planet_positions if p["house"] == 7],
                "second_house":    [p["name"] for p in planet_positions if p["house"] == 2],
                "indication":      "Marriage prospects indicated by " + ", ".join(marriage_lords_present) if marriage_lords_present else "Standard indications"
            }
        except Exception as e:
            result["marriage_error"] = str(e)

        # ── Mangal Dosha ─────────────────────────────────────────
        try:
            mars_positions = [p for p in planet_positions if p["name"] == "Mars"]
            mangal_dosha   = any(p["house"] in MANGAL_HOUSES for p in mars_positions)
            result["mangal_dosha"] = mangal_dosha
            if mangal_dosha and mars_positions:
                result["mangal_dosha_detail"] = f"Mars in house {mars_positions[0]['house']} — Mangal Dosha present"
            else:
                result["mangal_dosha_detail"] = "No Mangal Dosha"
        except Exception as e:
            result["mangal_error"] = str(e)

        # ── Yoga Detection ───────────────────────────────────────
        yoga_list = []
        try:
            for fn_name in ['yoga_details', 'get_yoga_details', 'get_yogas', 'calculate_yogas']:
                fn = getattr(yoga_module, fn_name, None)
                if fn:
                    raw_y = fn(jd, place)
                    if isinstance(raw_y, dict):
                        for k, v in list(raw_y.items())[:10]:
                            yoga_list.append({"name": str(k), "description": str(v)[:200]})
                    elif isinstance(raw_y, (list, tuple)):
                        for y in raw_y[:10]:
                            if isinstance(y, (list, tuple)):
                                yoga_list.append({"name": str(y[0]), "description": str(y[1]) if len(y) > 1 else ""})
                            else:
                                yoga_list.append({"name": str(y), "description": ""})
                    break
        except Exception:
            pass
        result["yogas"] = yoga_list

        # ── Narrative Predictions ────────────────────────────────
        predictions = []
        if "dasha_lord" in result:
            lord = result["dasha_lord"]
            predictions.append(f"Current Maha Dasha: {lord} — themes of {_lord_theme(lord)}")
        if result.get("mangal_dosha"):
            predictions.append("Mangal Dosha is present — consider remedies and compatible partner")
        if result.get("marriage_timing", {}).get("seventh_house"):
            planets_in_7 = ", ".join(result["marriage_timing"]["seventh_house"])
            predictions.append(f"Planets in 7th house ({planets_in_7}) influence partnership matters")
        if not predictions:
            predictions.append("Chart calculated successfully. Consult a qualified Jyotishi for personalised predictions.")
        result["predictions"] = predictions

        return result


def _lord_theme(lord):
    themes = {
        "Sun":     "leadership, authority, vitality, father",
        "Moon":    "emotions, home, mother, intuition",
        "Mars":    "energy, courage, conflict, ambition",
        "Mercury": "communication, business, intellect",
        "Jupiter": "wisdom, expansion, spirituality, wealth",
        "Venus":   "love, beauty, luxury, relationships",
        "Saturn":  "discipline, karma, delays, responsibility",
        "Rahu":    "ambition, illusion, foreign matters, technology",
        "Ketu":    "spirituality, detachment, past karma, moksha"
    }
    return themes.get(lord, "general planetary influences")
