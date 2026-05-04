from flask import Flask, render_template, request, jsonify, send_file
import sys
import os
import io
import json
from datetime import datetime, date

# ── path setup ─────────────────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
for d in [current_dir, src_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

# ── JHora core imports ──────────────────────────────────────────────────────
from jhora import utils, const
from jhora.panchanga import drik
from jhora.horoscope.chart import charts, yoga, dosha, strength
from jhora.horoscope.match import compatibility
from jhora.horoscope.dhasa.graha import vimsottari

utils.set_language(const.available_languages['English'])

PLANET_NAMES = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu", "Lagna"
]

RASI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# ── ASTRO_OS imports (graceful fallback) ────────────────────────────────────
try:
    from vedic_divisionals.varga_runtime import VargaRuntime
    _VARGA_RUNTIME = VargaRuntime()
    HAS_VARGAS = True
except Exception as e:
    HAS_VARGAS = False
    print(f"[WARN] VargaRuntime unavailable: {e}")

try:
    from ai.interpretation_engine import AIInterpretationEngine
    _AI_ENGINE = AIInterpretationEngine()
    HAS_AI = True
except Exception as e:
    HAS_AI = False
    print(f"[WARN] AI engine unavailable: {e}")

try:
    from prashna.kp_engine import KPEngine
    _KP_ENGINE = KPEngine()
    HAS_KP = True
except Exception as e:
    HAS_KP = False
    print(f"[WARN] KP engine unavailable: {e}")

try:
    from astro_map.astrocartography import AstroCartography
    _ASTROMAP = AstroCartography()
    HAS_ASTROMAP = True
except Exception as e:
    HAS_ASTROMAP = False
    print(f"[WARN] AstroCartography unavailable: {e}")

try:
    from dasha_core.full_dasha_engine import FullDashaEngine
    _DASHA_ENGINE = FullDashaEngine()
    HAS_DASHA_CORE = True
except Exception as e:
    HAS_DASHA_CORE = False
    print(f"[WARN] FullDashaEngine unavailable: {e}")

try:
    from export.exporter import Exporter
    _EXPORTER = Exporter()
    HAS_EXPORT = True
except Exception as e:
    HAS_EXPORT = False
    print(f"[WARN] Exporter unavailable: {e}")

try:
    from batch.batch_runner import BatchRunner
    _BATCH = BatchRunner()
    HAS_BATCH = True
except Exception as e:
    HAS_BATCH = False
    print(f"[WARN] BatchRunner unavailable: {e}")

try:
    from src.jhora.vedic_v4_predictor import VedicV4Predictor
    _V4 = VedicV4Predictor()
    HAS_V4 = True
except Exception:
    try:
        sys.path.insert(0, src_dir)
        from jhora.vedic_v4_predictor import VedicV4Predictor
        _V4 = VedicV4Predictor()
        HAS_V4 = True
    except Exception as e2:
        HAS_V4 = False
        print(f"[WARN] V4 Predictor unavailable: {e2}")

# ── Flask app ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'jhora_astro_os_secret_2024'

# ── helper utilities ────────────────────────────────────────────────────────
def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def jd_to_date_str(jd):
    try:
        g = utils.jd_to_gregorian(jd)
        return f"{int(g[2]):02d}-{int(g[1]):02d}-{int(g[0])}"
    except Exception:
        return "N/A"

def parse_birth_data(data):
    date_str   = data.get('date', '')
    time_str   = data.get('time', '12:00:00')
    place_name = data.get('place', 'Jaipur,IN')
    latitude   = float(data.get('latitude',  26.9124))
    longitude  = float(data.get('longitude', 75.7873))
    timezone   = float(data.get('timezone',  5.5))

    date_obj   = datetime.strptime(date_str, '%Y-%m-%d').date()
    parts      = time_str.replace('-', ':').split(':')
    hour       = int(parts[0])
    minute     = int(parts[1])
    second     = int(parts[2]) if len(parts) > 2 else 0

    place = drik.Place(place_name, latitude, longitude, timezone)
    jd    = utils.julian_day_number(
                (date_obj.year, date_obj.month, date_obj.day),
                (hour, minute, second))
    return place, jd, latitude, longitude, timezone

def get_planet_positions(jd, place):
    """Return list of dicts with full planet info."""
    raw = charts.rasi_chart(jd, place)
    positions = []
    for entry in raw:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            planet_id, pos = entry
            if isinstance(pos, (list, tuple)) and len(pos) == 2:
                rasi_idx, lon_in_rasi = pos
            else:
                rasi_idx, lon_in_rasi = 0, safe_float(pos)
        else:
            continue
        abs_lon = rasi_idx * 30.0 + safe_float(lon_in_rasi)
        # rasi_chart uses 'L' (string) for Lagna; ints for planets 0-8
        if planet_id == 'L':
            p_name = "Lagna"
            p_id   = 9
        elif isinstance(planet_id, int) and planet_id < len(PLANET_NAMES):
            p_name = PLANET_NAMES[planet_id]
            p_id   = planet_id
        else:
            try:
                p_id   = int(planet_id)
                p_name = PLANET_NAMES[p_id] if p_id < len(PLANET_NAMES) else f"P{p_id}"
            except Exception:
                p_name = str(planet_id)
                p_id   = -1
        positions.append({
            "id":          p_id,
            "name":        p_name,
            "rasi":        int(rasi_idx),
            "sign":        RASI_NAMES[int(rasi_idx) % 12],
            "house":       int(rasi_idx) + 1,
            "lon_in_sign": round(safe_float(lon_in_rasi), 4),
            "longitude":   round(abs_lon, 4)
        })
    return positions

# ── Page routes ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/panchanga')
def panchanga_page():
    return render_template('panchanga.html')

@app.route('/horoscope')
def horoscope_page():
    return render_template('horoscope.html')

@app.route('/divisional')
def divisional_page():
    return render_template('divisional.html')

@app.route('/dasha')
def dasha_page():
    return render_template('dasha.html')

@app.route('/compatibility')
def compatibility_page():
    return render_template('compatibility.html')

@app.route('/prashna')
def prashna_page():
    return render_template('prashna.html')

@app.route('/transit')
def transit_page():
    return render_template('transit.html')

@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/predictions')
def predictions_page():
    return render_template('predictions.html')

# ── API: Status ─────────────────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    try:
        with open(os.path.join(current_dir, 'VERSION.json')) as f:
            version = json.load(f)
    except Exception:
        version = {}
    return jsonify({
        "status": "online",
        "version": version,
        "engines": {
            "vargas": HAS_VARGAS,
            "ai":     HAS_AI,
            "kp":     HAS_KP,
            "astromap": HAS_ASTROMAP,
            "dasha_core": HAS_DASHA_CORE,
            "export": HAS_EXPORT,
            "batch":  HAS_BATCH,
            "v4_predictor": HAS_V4
        }
    })

# ── API: Panchanga ──────────────────────────────────────────────────────────
@app.route('/api/panchanga', methods=['POST'])
def calculate_panchanga():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        sunrise_raw  = drik.sunrise(jd, place)
        sunset_raw   = drik.sunset(jd, place)
        moonrise_raw = drik.moonrise(jd, place)
        moonset_raw  = drik.moonset(jd, place)

        def fmt_time(raw):
            try:
                t = raw[1] if isinstance(raw, (list, tuple)) and len(raw) > 1 else raw
                if isinstance(t, float):
                    h = int(t)
                    m = int((t - h) * 60)
                    return f"{h:02d}:{m:02d}"
                return str(t)
            except Exception:
                return "N/A"

        tithi_info     = drik.tithi(jd, place)
        nakshatra_info = drik.nakshatra(jd, place)
        yoga_info      = drik.yogam(jd, place)
        karana_info    = drik.karana(jd, place)
        rasi_info      = drik.raasi(jd, place)

        def safe_list(lst, idx, default='N/A'):
            try:
                return lst[idx]
            except Exception:
                return default

        t_idx = int(tithi_info[0]) - 1 if isinstance(tithi_info, (list, tuple)) else 0
        n_idx = int(nakshatra_info[0]) - 1 if isinstance(nakshatra_info, (list, tuple)) else 0
        n_pad = int(nakshatra_info[1]) if isinstance(nakshatra_info, (list, tuple)) and len(nakshatra_info) > 1 else 1
        y_idx = int(yoga_info[0]) - 1 if isinstance(yoga_info, (list, tuple)) else 0
        k_idx = int(karana_info[0]) - 1 if isinstance(karana_info, (list, tuple)) else 0
        r_idx = int(rasi_info[0]) - 1 if isinstance(rasi_info, (list, tuple)) else 0

        result = {
            'place':     f"{data.get('place')} ({lat:.4f}°, {lon:.4f}°)",
            'date':      data.get('date'),
            'time':      data.get('time', '12:00'),
            'sunrise':   fmt_time(sunrise_raw),
            'sunset':    fmt_time(sunset_raw),
            'moonrise':  fmt_time(moonrise_raw),
            'moonset':   fmt_time(moonset_raw),
            'tithi':     f"{safe_list(utils.TITHI_LIST, t_idx)} ({safe_list(utils.TITHI_DEITIES, t_idx)})",
            'nakshatra': f"{safe_list(utils.NAKSHATRA_LIST, n_idx)} - Pada {n_pad}",
            'yoga':      safe_list(utils.YOGAM_LIST, y_idx),
            'karana':    safe_list(utils.KARANA_LIST, k_idx),
            'rasi':      safe_list(utils.RAASI_LIST, r_idx),
            'vaara':     utils.DAYS_LIST[drik.vaara(jd)]
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Horoscope ──────────────────────────────────────────────────────────
@app.route('/api/horoscope', methods=['POST'])
def calculate_horoscope():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        # get_planet_positions already includes Lagna ('L') from rasi_chart
        positions = get_planet_positions(jd, place)

        # Yogas — try known yoga functions
        yoga_results = []
        try:
            for fn_name in ['yoga_details', 'get_yoga_details', 'get_yogas', 'calculate_yogas']:
                fn = getattr(yoga, fn_name, None)
                if fn:
                    raw = fn(jd, place)
                    if isinstance(raw, dict):
                        for k, v in list(raw.items())[:10]:
                            yoga_results.append({'name': str(k), 'description': str(v)[:200]})
                    elif isinstance(raw, (list, tuple)):
                        for y_item in raw[:10]:
                            if isinstance(y_item, (list, tuple)):
                                yoga_results.append({'name': str(y_item[0]), 'description': str(y_item[1]) if len(y_item) > 1 else ''})
                            else:
                                yoga_results.append({'name': str(y_item), 'description': ''})
                    break
        except Exception:
            pass

        # Doshas — use get_dosha_details (returns HTML dict)
        dosha_results = {}
        try:
            import re as _re
            raw_dosha = dosha.get_dosha_details(jd, place)
            if isinstance(raw_dosha, dict):
                for k, v in raw_dosha.items():
                    clean = _re.sub(r'<[^>]+>', ' ', str(v)).strip()
                    dosha_results[k] = clean[:300]
        except Exception:
            pass

        # Strength — use shad_bala
        strength_results = {}
        try:
            sb = strength.shad_bala(jd, place)
            if isinstance(sb, (list, tuple)):
                for i, val in enumerate(sb[:9]):
                    p_name = PLANET_NAMES[i] if i < len(PLANET_NAMES) else f"P{i}"
                    try:
                        strength_results[p_name] = round(float(val), 3)
                    except Exception:
                        strength_results[p_name] = str(val)
            elif isinstance(sb, dict):
                strength_results = {str(k): v for k, v in sb.items()}
        except Exception:
            pass

        # AI interpretation
        interpretation = {}
        if HAS_AI:
            try:
                chart_summary = {"planets": [p['name'] + " in " + p['sign'] for p in positions]}
                interpretation = _AI_ENGINE.interpret(chart_summary)
            except Exception:
                pass

        return jsonify({
            'planets':        positions,
            'yogas':          yoga_results,
            'doshas':         dosha_results,
            'strength':       strength_results,
            'interpretation': interpretation
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Divisional Charts ──────────────────────────────────────────────────
@app.route('/api/divisional', methods=['POST'])
def calculate_divisional():
    try:
        data      = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)
        division  = data.get('division', 'all')

        positions = get_planet_positions(jd, place)
        # Build position dict keyed by name for VargaRuntime
        pos_dict = {p['name']: {"longitude": p['longitude']} for p in positions}

        if not HAS_VARGAS:
            return jsonify({'error': 'Divisional chart engine not available'}), 503

        vargas = _VARGA_RUNTIME.build(pos_dict)

        if division != 'all' and division in vargas:
            result = {division: vargas[division]}
        else:
            result = vargas

        # Convert numeric sign indices to sign names for readability
        readable = {}
        for varga_name, planet_map in result.items():
            readable[varga_name] = {}
            for planet, lon in planet_map.items():
                sign_idx = int(lon // 30) % 12
                readable[varga_name][planet] = {
                    "longitude":    round(float(lon), 2),
                    "sign_index":   sign_idx,
                    "sign":         RASI_NAMES[sign_idx]
                }

        return jsonify({'vargas': readable, 'base_planets': positions})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Dhasa ──────────────────────────────────────────────────────────────
@app.route('/api/dhasa', methods=['POST'])
def calculate_dhasa():
    try:
        data       = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)
        dhasa_type = data.get('dhasa_type', 'vimsottari')

        if dhasa_type == 'vimsottari':
            # get_vimsottari_dhasa_bhukthi returns (start_info, periods_list)
            # periods_list items: [maha_lord_id, antar_lord_id, start_date_str]
            raw = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)
            if isinstance(raw, (list, tuple)) and len(raw) == 2 and isinstance(raw[1], list):
                _start_info, periods_list = raw
            else:
                periods_list = list(raw) if raw else []

            results = []
            for i, period in enumerate(periods_list[:60]):
                try:
                    maha_id  = period[0]
                    antar_id = period[1]
                    start_dt = str(period[2]) if len(period) > 2 else "N/A"
                    end_dt   = str(periods_list[i + 1][2]) if i + 1 < len(periods_list) else "N/A"
                    def _pid_name(pid):
                        if isinstance(utils.PLANET_NAMES, dict):
                            return utils.PLANET_NAMES.get(pid, PLANET_NAMES[pid] if isinstance(pid,int) and pid<len(PLANET_NAMES) else str(pid))
                        return PLANET_NAMES[pid] if isinstance(pid,int) and pid<len(PLANET_NAMES) else str(pid)
                    results.append({
                        'planet':     _pid_name(maha_id),
                        'sub_planet': _pid_name(antar_id),
                        'start_date': start_dt,
                        'end_date':   end_dt,
                    })
                except Exception:
                    continue
        else:
            results = [{'error': f'Dhasa type "{dhasa_type}" not yet implemented'}]

        return jsonify({'periods': results, 'dhasa_type': dhasa_type})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Full Dasha (ASTRO_OS engine) ──────────────────────────────────────
@app.route('/api/dasha/full', methods=['POST'])
def calculate_dasha_full():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        # Determine Moon's nakshatra lord for starting dasha
        nakshatra_info = drik.nakshatra(jd, place)
        n_idx = int(nakshatra_info[0]) if isinstance(nakshatra_info, (list, tuple)) else 1

        DASHA_LORDS = [
            "Ketu", "Venus", "Sun", "Moon", "Mars",
            "Rahu", "Jupiter", "Saturn", "Mercury"
        ]
        NAK_LORDS = [
            "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
            "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
            "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
        ]
        start_lord = NAK_LORDS[(n_idx - 1) % 27]

        if HAS_DASHA_CORE:
            result = _DASHA_ENGINE.build(start_lord, jd)
            return jsonify({
                'start_lord': start_lord,
                'maha_dashas': result.get('maha', []),
                'antar_dashas': result.get('antar', [])[:27]
            })
        else:
            return jsonify({'error': 'Full dasha engine not available', 'start_lord': start_lord}), 503

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Compatibility ──────────────────────────────────────────────────────
@app.route('/api/compatibility', methods=['POST'])
def calculate_compatibility():
    try:
        data      = request.json
        boy_star  = int(data.get('boy_star', 1))
        boy_pada  = int(data.get('boy_pada', 1))
        girl_star = int(data.get('girl_star', 1))
        girl_pada = int(data.get('girl_pada', 1))

        comp = compatibility.Ashtakoota(boy_star, boy_pada, girl_star, girl_pada)
        raw_result = comp.compatibility_score()

        # compatibility_score() returns a flat list:
        # [s0,s1,s2,s3,s4,s5,s6,s7, total, n0,n1,n2,n3]
        # where s0-s7 = 8 ettu porutham scores,
        # total = overall score, n0-n3 = naalu porutham booleans
        if isinstance(raw_result, (list, tuple)) and len(raw_result) == 13:
            ettu_porutham  = list(raw_result[:8])
            total_score    = raw_result[8]
            naalu_porutham = list(raw_result[9:13])
        elif isinstance(raw_result, (list, tuple)) and len(raw_result) == 3:
            ettu_porutham, total_score, naalu_porutham = raw_result
        else:
            # fallback: treat entire list as ettu scores, compute total
            ettu_porutham  = list(raw_result) if raw_result else [0]*8
            total_score    = sum(float(x) for x in ettu_porutham if isinstance(x, (int, float)))
            naalu_porutham = []

        porutham_names = [
            'Varna', 'Vasya', 'Gana', 'Nakshatra',
            'Yoni', 'Rasi Adhipati', 'Rasi', 'Nadi'
        ]
        max_scores = [1, 2, 6, 4, 4, 5, 7, 8]
        results = []
        for i, (score, max_s) in enumerate(zip(ettu_porutham, max_scores)):
            try:
                pct = round((float(score) / max_s) * 100, 1)
            except Exception:
                pct = 0
            results.append({
                'name':       porutham_names[i],
                'score':      score,
                'max_score':  max_s,
                'percentage': pct
            })

        naalu_names = ['Mahendra', 'Vedha', 'Rajju', 'Sthree Dheerga']
        for i, res in enumerate(naalu_porutham):
            results.append({
                'name':       naalu_names[i],
                'score':      'Yes' if res else 'No',
                'max_score':  'Yes',
                'percentage': 100 if res else 0
            })

        try:
            max_compat = compatibility.max_compatibility_score
        except AttributeError:
            max_compat = 36
        overall_pct = round((float(total_score) / max_compat) * 100, 1)

        return jsonify({
            'results':           results,
            'total_score':       total_score,
            'max_total':         compatibility.max_compatibility_score,
            'overall_percentage': overall_pct,
            'boy_star':          utils.NAKSHATRA_LIST[boy_star - 1],
            'girl_star':         utils.NAKSHATRA_LIST[girl_star - 1]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: KP Prashna ─────────────────────────────────────────────────────────
@app.route('/api/prashna', methods=['POST'])
def calculate_prashna():
    try:
        data     = request.json
        question = data.get('question', '')
        score    = float(data.get('score', 0))

        if not HAS_KP:
            return jsonify({'error': 'KP engine not available'}), 503

        answer = _KP_ENGINE.decide(score)

        # Get current planetary positions for prashna chart
        now_jd = utils.julian_day_number(
            (datetime.now().year, datetime.now().month, datetime.now().day),
            (datetime.now().hour, datetime.now().minute, datetime.now().second))
        now_place = drik.Place('Query Location', 26.9124, 75.7873, 5.5)
        positions = get_planet_positions(now_jd, now_place)

        return jsonify({
            'question': question,
            'answer':   answer,
            'score':    score,
            'prashna_chart': positions,
            'interpretation': f"KP Analysis: The query receives answer '{answer}'. "
                              f"Score {score:+.2f} indicates "
                              f"{'favourable' if score > 0 else 'unfavourable' if score < 0 else 'neutral'} outcome."
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Current Transits ───────────────────────────────────────────────────
@app.route('/api/transit', methods=['POST'])
def calculate_transit():
    try:
        data  = request.json
        place_name = data.get('place', 'Jaipur,IN')
        lat   = float(data.get('latitude', 26.9124))
        lon   = float(data.get('longitude', 75.7873))
        tz    = float(data.get('timezone', 5.5))

        now      = datetime.now()
        now_place = drik.Place(place_name, lat, lon, tz)
        now_jd    = utils.julian_day_number(
            (now.year, now.month, now.day),
            (now.hour, now.minute, now.second))

        current_positions = get_planet_positions(now_jd, now_place)

        # Panchanga for today
        try:
            tithi_raw = drik.tithi(now_jd, now_place)
            t_idx = int(tithi_raw[0]) - 1 if isinstance(tithi_raw, (list, tuple)) else 0
            current_tithi = utils.TITHI_LIST[t_idx]
        except Exception:
            current_tithi = "N/A"

        return jsonify({
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'planets':   current_positions,
            'tithi':     current_tithi,
            'vaara':     utils.DAYS_LIST[drik.vaara(now_jd)]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: AI Interpretation ──────────────────────────────────────────────────
@app.route('/api/interpret', methods=['POST'])
def api_interpret():
    try:
        data = request.json
        chart = data.get('chart', {})

        if not HAS_AI:
            return jsonify({'error': 'AI engine not available'}), 503

        result = _AI_ENGINE.interpret(chart)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Astrocartography ───────────────────────────────────────────────────
@app.route('/api/astromap', methods=['POST'])
def calculate_astromap():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        positions = get_planet_positions(jd, place)
        pos_dict  = {p['name']: {"longitude": p['longitude']} for p in positions}

        if not HAS_ASTROMAP:
            return jsonify({'error': 'Astrocartography engine not available'}), 503

        projection = _ASTROMAP.project(pos_dict)
        return jsonify({'projection': projection, 'planets': positions})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Export ─────────────────────────────────────────────────────────────
@app.route('/api/export', methods=['POST'])
def api_export():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        positions = get_planet_positions(jd, place)
        export_data = {
            'birth_data': data,
            'julian_day': jd,
            'planets':    positions,
            'generated':  datetime.now().isoformat()
        }

        # Add vargas if available
        if HAS_VARGAS:
            pos_dict = {p['name']: {"longitude": p['longitude']} for p in positions}
            export_data['vargas'] = _VARGA_RUNTIME.build(pos_dict)

        # Save to a temp file and stream it back
        out_path = os.path.join(current_dir, 'static', 'chart_export.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        return send_file(out_path, mimetype='application/json',
                         as_attachment=True,
                         download_name='chart_export.json')

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Batch ──────────────────────────────────────────────────────────────
@app.route('/api/batch', methods=['POST'])
def api_batch():
    try:
        data  = request.json
        start = float(data.get('start_jd', 2460000.0))
        end   = float(data.get('end_jd',   2460010.0))
        step  = float(data.get('step_jd',  1.0))

        if not HAS_BATCH:
            return jsonify({'error': 'Batch runner not available'}), 503

        jd_list = _BATCH.run(start, end, step)
        return jsonify({'jd_list': jd_list, 'count': len(jd_list)})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: V4 Predictions ─────────────────────────────────────────────────────
@app.route('/api/predictions', methods=['POST'])
def api_predictions():
    try:
        data = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)

        if not HAS_V4:
            # Fallback: build predictions from available data
            positions = get_planet_positions(jd, place)
            nakshatra_info = drik.nakshatra(jd, place)
            n_idx = int(nakshatra_info[0]) if isinstance(nakshatra_info, (list, tuple)) else 1
            NAK_LORDS = [
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
            ]
            start_lord = NAK_LORDS[(n_idx - 1) % 27]
            return jsonify({
                'dasha_lord': start_lord,
                'predictions': [
                    f"Current Vimshottari Dasha lord: {start_lord}",
                    "This period brings themes aligned with " + start_lord + " energy.",
                    "Consult a qualified Jyotishi for detailed personal predictions."
                ],
                'note': 'V4 predictor unavailable — basic predictions shown'
            })

        result = _V4.predict(jd, place)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Full Chart (ASTRO_OS core engine) ──────────────────────────────────
@app.route('/api/chart/full', methods=['POST'])
def api_chart_full():
    try:
        data  = request.json
        place, jd, lat, lon, tz = parse_birth_data(data)
        positions = get_planet_positions(jd, place)

        result = {
            'julian_day': jd,
            'planets':    positions,
        }

        # Divisional charts
        if HAS_VARGAS:
            pos_dict = {p['name']: {"longitude": p['longitude']} for p in positions}
            vargas   = _VARGA_RUNTIME.build(pos_dict)
            readable = {}
            for vname, pmap in vargas.items():
                readable[vname] = {}
                for pn, lval in pmap.items():
                    sign_idx = int(lval // 30) % 12
                    readable[vname][pn] = {"longitude": round(float(lval), 2),
                                           "sign": RASI_NAMES[sign_idx]}
            result['vargas'] = readable

        # Dasha
        if HAS_DASHA_CORE:
            nakshatra_info = drik.nakshatra(jd, place)
            n_idx = int(nakshatra_info[0]) if isinstance(nakshatra_info, (list, tuple)) else 1
            NAK_LORDS = [
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
                "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
            ]
            start_lord  = NAK_LORDS[(n_idx - 1) % 27]
            dasha_result = _DASHA_ENGINE.build(start_lord, jd)
            result['dasha'] = dasha_result

        # AI interpretation
        if HAS_AI:
            chart_summary = {"planets": [p['name'] + " in " + p['sign'] for p in positions]}
            result['interpretation'] = _AI_ENGINE.interpret(chart_summary)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static',    exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
