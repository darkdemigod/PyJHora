from flask import Flask, render_template, request, jsonify, send_file
import sys
import os
import io
import json
import re
import uuid
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename

# ── path setup ─────────────────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
for d in [current_dir, src_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

# ── JHora core imports ──────────────────────────────────────────────────────
from jhora import utils, const
from jhora.panchanga import drik
from jhora.horoscope.chart import charts, yoga, dosha, strength, raja_yoga
from jhora.horoscope.match import compatibility
from jhora.horoscope.dhasa.graha import vimsottari

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

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
app.config['UPLOAD_FOLDER'] = os.path.join(current_dir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── In-memory stores ─────────────────────────────────────────────────────────
_chart_cache = {}   # chart_id -> full chart data dict
_book_store   = {}  # book_id  -> {filename, text, chunks, rules}

# ── Constants ────────────────────────────────────────────────────────────────
DASHA_YEARS_BY_ID  = [6, 10, 7, 17, 16, 20, 19, 18, 7]  # Sun..Ketu
SHAD_BALA_LABELS   = ['Sthana','Dig','Kala','Chesta','Naisargika','Drik',
                       'Total Rupa','Required','Ratio']
SHAD_BALA_PLANETS  = ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn']
ASTRO_KEYWORDS     = {
    'planets' : ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu','Lagna'],
    'signs'   : ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra',
                 'Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'],
    'yoga'    : ['yoga','dosha','conjunction','aspect','exalted','debilitated',
                 'retrograde','kendra','trine','dharma','karma','raja','dhana'],
    'house'   : ['house','bhava','lagna','ascendant','lord','sthana'],
    'dasha'   : ['dasha','mahadasha','antardasha','bhukti','period','transit'],
    'predict' : ['gives','causes','results','indicates','shows','produces',
                 'brings','native','person','born','will'],
}
RASI_SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
               'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

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
    place_name = data.get('place', 'Jaipur,IN')
    latitude   = float(data.get('latitude',  26.9124))
    longitude  = float(data.get('longitude', 75.7873))
    timezone   = float(data.get('timezone',  5.5))

    # Support both individual fields (year/month/day/hour/minute) and date/time strings
    if 'year' in data:
        year   = int(data['year'])
        month  = int(data.get('month',  1))
        day    = int(data.get('day',    1))
        hour   = int(data.get('hour',   6))
        minute = int(data.get('minute', 0))
        second = int(data.get('second', 0))
    else:
        date_str = data.get('date', '')
        time_str = data.get('time', '6:00:00')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        year, month, day = date_obj.year, date_obj.month, date_obj.day
        parts  = time_str.replace('-', ':').split(':')
        hour   = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0

    place = drik.Place(place_name, latitude, longitude, timezone)
    jd    = utils.julian_day_number(
                (year, month, day),
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

# ── Dasha helpers ────────────────────────────────────────────────────────────
def _compute_pratyantara(start_str, end_str):
    """Compute pratyantara (3rd level) dasha periods proportionally."""
    try:
        fmt   = '%Y-%m-%d %H:%M:%S'
        start = datetime.strptime(start_str[:19], fmt)
        end   = datetime.strptime(end_str[:19],   fmt)
        dur   = (end - start).total_seconds()
        total = sum(DASHA_YEARS_BY_ID)
        result, cursor = [], start
        for pid, yrs in enumerate(DASHA_YEARS_BY_ID):
            p_end = cursor + timedelta(seconds=(yrs / total) * dur)
            result.append({'planet': PLANET_NAMES[pid],
                           'start_date': cursor.strftime(fmt),
                           'end_date':   p_end.strftime(fmt)})
            cursor = p_end
        return result
    except Exception:
        return []

# ── Rule extraction helpers ───────────────────────────────────────────────────
def _score_astro_relevance(text):
    tl, score = text.lower(), 0
    for kws in ASTRO_KEYWORDS.values():
        hits = sum(1 for kw in kws if kw.lower() in tl)
        if hits: score += 1 + min(hits, 4)
    return score

def _extract_rules(text, min_score=3):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    rules = []
    for sent in sentences:
        sent = sent.strip()
        if not (40 <= len(sent) <= 700): continue
        score = _score_astro_relevance(sent)
        if score < min_score: continue
        sl   = sent.lower()
        cats = []
        if any(w in sl for w in ASTRO_KEYWORDS['yoga']):  cats.append('yoga')
        if any(w in sl for w in ASTRO_KEYWORDS['dasha']): cats.append('dasha')
        if any(w in sl for w in ASTRO_KEYWORDS['house']): cats.append('house')
        if not cats: cats.append('general')
        rules.append({
            'text':       sent,
            'score':      score,
            'categories': cats,
            'planets':    [p for p in PLANET_NAMES[:9] if p.lower() in sl],
            'signs':      [s for s in RASI_SIGNS         if s.lower() in sl],
        })
    rules.sort(key=lambda r: r['score'], reverse=True)
    return rules

def _match_rules_to_chart(rules, positions):
    planet_signs = {p['name']: p['sign'] for p in positions}
    matched = []
    for rule in rules:
        rel = 0
        for pl in rule.get('planets', []):
            if pl in planet_signs:
                rel += 2
                if planet_signs[pl] in rule.get('signs', []): rel += 4
        if rel > 0:
            matched.append({**rule, 'chart_relevance': rel})
    matched.sort(key=lambda r: r['chart_relevance'], reverse=True)
    return matched[:25]

def _deep_interpret(positions, raja_yogas, doshas, shad_bala, matched_rules=None):
    """Generate paragraph-level astrological interpretation."""
    paras = []
    EXALT = {'Sun':'Aries','Moon':'Taurus','Mars':'Capricorn','Mercury':'Virgo',
             'Jupiter':'Cancer','Venus':'Pisces','Saturn':'Libra',
             'Rahu':'Gemini','Ketu':'Sagittarius'}
    DEBIL = {'Sun':'Libra','Moon':'Scorpio','Mars':'Cancer','Mercury':'Pisces',
             'Jupiter':'Capricorn','Venus':'Virgo','Saturn':'Aries',
             'Rahu':'Sagittarius','Ketu':'Gemini'}
    SIGN_DESC = {
        'Aries':'energetic, pioneering, and assertive',
        'Taurus':'steadfast, sensual, and materially grounded',
        'Gemini':'communicative, versatile, and intellectually curious',
        'Cancer':'nurturing, emotionally sensitive, and home-oriented',
        'Leo':'regal, creative, and leadership-focused',
        'Virgo':'analytical, service-oriented, and detail-conscious',
        'Libra':'harmonious, relationship-focused, and justice-seeking',
        'Scorpio':'intense, transformative, and depth-seeking',
        'Sagittarius':'philosophical, expansive, and truth-seeking',
        'Capricorn':'disciplined, achievement-oriented, and structured',
        'Aquarius':'innovative, humanitarian, and unconventional',
        'Pisces':'compassionate, mystical, and spiritually attuned',
    }
    lagna = next((p for p in positions if p['name'] == 'Lagna'), None)
    if lagna:
        desc = SIGN_DESC.get(lagna['sign'], 'qualities of this sign')
        paras.append({'title': f"{lagna['sign']} Ascendant — Core Personality",
            'text': (f"The Lagna (Ascendant) is in {lagna['sign']} at {lagna['lon_in_sign']:.2f}°. "
                     f"This makes the native {desc}. The Lagna lord and its dispositor "
                     f"colour every facet of the native's life-path and self-expression."),
            'category': 'lagna', 'icon': '↑'})
    for p in positions:
        if p['name'] == 'Lagna': continue
        if p['sign'] == EXALT.get(p['name']):
            paras.append({'title': f"{p['name']} Exalted in {p['sign']}",
                'text': (f"{p['name']} occupies its sign of exaltation ({p['sign']}), conferring exceptional "
                         f"strength. Its bhava flourishes and during {p['name']}'s dasha the native "
                         f"can expect peak results in areas governed by this planet."),
                'category': 'dignity', 'icon': '⬆'})
        elif p['sign'] == DEBIL.get(p['name']):
            paras.append({'title': f"{p['name']} Debilitated in {p['sign']}",
                'text': (f"{p['name']} is in debilitation ({p['sign']}). A Neecha Bhanga may apply. "
                         f"Remediation through mantra, gemstones, or charity aligned with {p['name']} is advisable."),
                'category': 'dignity', 'icon': '⬇'})
    if raja_yogas:
        paras.append({'title': f"{len(raja_yogas)} Raja Yoga(s) Detected",
            'text': (f"The chart contains {len(raja_yogas)} Raja Yoga formation(s) arising from dharma-karma "
                     f"house lord combinations. These bestow status, recognition, and achievement — "
                     f"most powerfully during the dashas of the participating planets."),
            'category': 'yoga', 'icon': '👑'})
        for ry in raja_yogas:
            txt = ry.get('effect') or ry.get('description', '')
            if txt:
                paras.append({'title': ry.get('name', 'Raja Yoga'),
                    'text': txt[:500] + ('…' if len(txt) > 500 else ''),
                    'category': 'yoga_detail', 'icon': '☽',
                    'pairs': ry.get('pairs', '')})
    if shad_bala and 'totals' in shad_bala:
        totals = shad_bala['totals']
        strong = [p for p, v in totals.items() if v >= 150]
        weak   = [p for p, v in totals.items() if v <  80]
        if strong:
            paras.append({'title': 'Planets of Superior Strength',
                'text': (f"{', '.join(strong)} show superior Shad Bala strength. They deliver results "
                         f"powerfully during their dasha periods and strengthen any house they occupy or aspect."),
                'category': 'strength', 'icon': '💪'})
        if weak:
            paras.append({'title': 'Planets Requiring Remediation',
                'text': (f"{', '.join(weak)} carry below-threshold Shad Bala. Gemstone therapy, mantra japa, "
                         f"and charitable acts aligned with these planets can strengthen their benefic influence."),
                'category': 'strength', 'icon': '🔻'})
    active = [k for k, v in doshas.items()
              if 'no' not in str(v).lower() and 'not' not in str(v).lower()]
    if active:
        paras.append({'title': 'Doshas Present',
            'text': (f"Active doshas: {', '.join(active)}. Each represents a karmic pattern requiring "
                     f"targeted remedies. A qualified Jyotishi can prescribe personalised remediation."),
            'category': 'dosha', 'icon': '⚠'})
    if matched_rules:
        paras.append({'title': f"{len(matched_rules)} Classical Rules Matched to This Chart",
            'text': (f"Analysis of uploaded classical texts found {len(matched_rules)} rules directly "
                     f"applicable to this chart — providing depth beyond standard algorithmic interpretation."),
            'category': 'classical', 'icon': '📚'})
    return paras

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

        # Shad Bala — structured matrix (sb[component][planet])
        shad_bala_data = {}
        try:
            sb = strength.shad_bala(jd, place)
            if isinstance(sb, (list, tuple)) and len(sb) > 0:
                n_comp = len(sb)
                matrix = []
                for i in range(n_comp):
                    row = []
                    comp_row = sb[i] if isinstance(sb[i], (list, tuple)) else []
                    for j in range(len(SHAD_BALA_PLANETS)):
                        try:
                            row.append(round(float(comp_row[j]), 2))
                        except Exception:
                            row.append(0.0)
                    matrix.append(row)
                totals = {}
                for j, pname in enumerate(SHAD_BALA_PLANETS):
                    try:
                        total = round(float(sb[6][j]), 2) if n_comp > 6 else round(sum(float(sb[i][j]) for i in range(min(6,n_comp)) if isinstance(sb[i],(list,tuple)) and j < len(sb[i])), 2)
                    except Exception:
                        total = 0.0
                    totals[pname] = total
                shad_bala_data = {
                    'labels':  SHAD_BALA_LABELS[:n_comp],
                    'planets': SHAD_BALA_PLANETS,
                    'matrix':  matrix,
                    'totals':  totals,
                }
        except Exception:
            pass

        # Raja Yogas
        raja_yogas = []
        try:
            rj = raja_yoga.get_raja_yoga_details(jd, place)
            if isinstance(rj, tuple) and len(rj) >= 1 and isinstance(rj[0], dict):
                for yname, ydata in rj[0].items():
                    raja_yogas.append({
                        'type':        yname,
                        'pairs':       str(ydata[0]) if len(ydata) > 0 else '',
                        'name':        str(ydata[1]) if len(ydata) > 1 else yname,
                        'description': str(ydata[2]) if len(ydata) > 2 else '',
                        'effect':      str(ydata[3])[:600] if len(ydata) > 3 else '',
                    })
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

        # Cache for /api/interpret/<chart_id>
        chart_id = str(uuid.uuid4())[:12]
        _chart_cache[chart_id] = {
            'birth_data':     data,
            'planets':        positions,
            'yogas':          yoga_results,
            'raja_yogas':     raja_yogas,
            'doshas':         dosha_results,
            'shad_bala':      shad_bala_data,
            'interpretation': interpretation,
        }
        if len(_chart_cache) > 200:
            del _chart_cache[next(iter(_chart_cache))]

        return jsonify({
            'chart_id':       chart_id,
            'planets':        positions,
            'yogas':          yoga_results,
            'raja_yogas':     raja_yogas,
            'doshas':         dosha_results,
            'shad_bala':      shad_bala_data,
            'interpretation': interpretation,
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

        def pid_name(pid):
            if isinstance(utils.PLANET_NAMES, dict):
                return utils.PLANET_NAMES.get(pid, PLANET_NAMES[pid] if isinstance(pid, int) and pid < len(PLANET_NAMES) else str(pid))
            return PLANET_NAMES[pid] if isinstance(pid, int) and pid < len(PLANET_NAMES) else str(pid)

        if dhasa_type == 'vimsottari':
            raw = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)
            if isinstance(raw, (list, tuple)) and len(raw) == 2 and isinstance(raw[1], list):
                _start_info, periods_list = raw
            else:
                periods_list = list(raw) if raw else []

            include_tree = data.get('tree', False)
            if include_tree:
                tree = []
                maha_idx = {}
                for i, period in enumerate(periods_list):
                    try:
                        maha_id  = period[0]
                        antar_id = period[1]
                        start_dt = str(period[2]) if len(period) > 2 else "N/A"
                        end_dt   = str(periods_list[i + 1][2]) if i + 1 < len(periods_list) else "N/A"
                        antar_entry = {
                            'planet':       pid_name(antar_id),
                            'start_date':   start_dt,
                            'end_date':     end_dt,
                            'pratyantara':  _compute_pratyantara(start_dt, end_dt),
                        }
                        if maha_id not in maha_idx:
                            maha_idx[maha_id] = len(tree)
                            tree.append({'planet': pid_name(maha_id), 'start_date': start_dt, 'antar': []})
                        tree[maha_idx[maha_id]]['antar'].append(antar_entry)
                    except Exception:
                        continue
                return jsonify({'tree': tree, 'dhasa_type': dhasa_type})

            results = []
            for i, period in enumerate(periods_list[:60]):
                try:
                    results.append({
                        'planet':     pid_name(period[0]),
                        'sub_planet': pid_name(period[1]),
                        'start_date': str(period[2]) if len(period) > 2 else "N/A",
                        'end_date':   str(periods_list[i + 1][2]) if i + 1 < len(periods_list) else "N/A",
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

# ── API: Deep Interpretation (POST) ─────────────────────────────────────────
@app.route('/api/interpret', methods=['POST'])
def api_interpret():
    try:
        data    = request.json
        book_id = data.get('book_id')
        # If chart_id supplied, re-interpret cached chart
        cid = data.get('chart_id')
        if cid and cid in _chart_cache:
            cached = _chart_cache[cid]
            matched = _match_rules_to_chart(
                _book_store.get(book_id, {}).get('rules', []) if book_id else [],
                cached['planets'])
            paras = _deep_interpret(cached['planets'], cached.get('raja_yogas',[]),
                                    cached.get('doshas',{}), cached.get('shad_bala',{}), matched)
            return jsonify({**cached, 'paragraphs': paras, 'matched_rules': matched})

        place, jd, lat, lon, tz = parse_birth_data(data)
        positions = get_planet_positions(jd, place)

        raja_yogas = []
        try:
            rj = raja_yoga.get_raja_yoga_details(jd, place)
            if isinstance(rj, tuple) and isinstance(rj[0], dict):
                for yname, ydata in rj[0].items():
                    raja_yogas.append({'type': yname,
                        'pairs': str(ydata[0]) if ydata else '',
                        'name': str(ydata[1]) if len(ydata) > 1 else yname,
                        'description': str(ydata[2]) if len(ydata) > 2 else '',
                        'effect': str(ydata[3])[:600] if len(ydata) > 3 else ''})
        except Exception:
            pass

        doshas = {}
        try:
            raw_d = dosha.get_dosha_details(jd, place)
            if isinstance(raw_d, dict):
                for k, v in raw_d.items():
                    doshas[k] = re.sub(r'<[^>]+>', ' ', str(v)).strip()[:300]
        except Exception:
            pass

        shad_bala = {}
        try:
            sb = strength.shad_bala(jd, place)
            if isinstance(sb, (list, tuple)) and len(sb) > 6:
                totals = {pname: round(float(sb[6][j]), 2)
                          for j, pname in enumerate(SHAD_BALA_PLANETS)
                          if isinstance(sb[6], (list, tuple)) and j < len(sb[6])}
                shad_bala = {'totals': totals, 'planets': SHAD_BALA_PLANETS}
        except Exception:
            pass

        matched = _match_rules_to_chart(
            _book_store.get(book_id, {}).get('rules', []) if book_id else [],
            positions)
        paras   = _deep_interpret(positions, raja_yogas, doshas, shad_bala, matched)

        chart_id = str(uuid.uuid4())[:12]
        result = {'chart_id': chart_id, 'planets': positions, 'raja_yogas': raja_yogas,
                  'doshas': doshas, 'shad_bala': shad_bala,
                  'matched_rules': matched, 'paragraphs': paras}
        _chart_cache[chart_id] = result
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Deep Interpretation by chart_id (GET) ───────────────────────────────
@app.route('/api/interpret/<chart_id>', methods=['GET'])
def api_interpret_by_id(chart_id):
    try:
        if chart_id not in _chart_cache:
            return jsonify({'error': 'Chart not found. Recalculate horoscope first.'}), 404
        book_id = request.args.get('book_id')
        cached  = _chart_cache[chart_id]
        matched = _match_rules_to_chart(
            _book_store.get(book_id, {}).get('rules', []) if book_id else [],
            cached['planets'])
        paras = _deep_interpret(cached['planets'], cached.get('raja_yogas', []),
                                cached.get('doshas', {}), cached.get('shad_bala', {}), matched)
        return jsonify({**cached, 'paragraphs': paras, 'matched_rules': matched})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: PDF Upload ───────────────────────────────────────────────────────────
@app.route('/api/pdf/upload', methods=['POST'])
def api_pdf_upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file field in request'}), 400
        f = request.files['file']
        if not f.filename:
            return jsonify({'error': 'No filename'}), 400
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        if not HAS_PYPDF:
            return jsonify({'error': 'pypdf not installed on server'}), 503

        fname     = secure_filename(f.filename)
        book_id   = str(uuid.uuid4())[:10]
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{book_id}_{fname}")
        f.save(save_path)

        reader     = pypdf.PdfReader(save_path)
        pages_text = []
        for page in reader.pages:
            try: pages_text.append(page.extract_text() or '')
            except Exception: pages_text.append('')
        full_text = '\n\n'.join(pages_text)

        chunks = [c.strip() for c in re.split(r'\n{2,}', full_text) if len(c.strip()) > 60]
        rules  = _extract_rules(full_text, min_score=3)
        _book_store[book_id] = {'filename': fname, 'pages': len(reader.pages),
                                 'text': full_text, 'chunks': chunks,
                                 'rules': rules, 'save_path': save_path}
        return jsonify({'book_id': book_id, 'filename': fname,
                        'pages': len(reader.pages), 'chars': len(full_text),
                        'chunks': len(chunks), 'rules': len(rules),
                        'preview': full_text[:600] + ('…' if len(full_text) > 600 else '')})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: List Books ───────────────────────────────────────────────────────────
@app.route('/api/books', methods=['GET'])
def api_books_list():
    return jsonify({'books': [
        {'book_id': bid, 'filename': v['filename'], 'pages': v['pages'],
         'chunks': len(v['chunks']), 'rules': len(v['rules'])}
        for bid, v in _book_store.items()
    ]})

# ── API: Parse Rules from Book ────────────────────────────────────────────────
@app.route('/api/books/<book_id>/parse-rules', methods=['GET'])
def api_parse_rules(book_id):
    try:
        if book_id not in _book_store:
            return jsonify({'error': 'Book not found'}), 404
        book      = _book_store[book_id]
        min_score = int(request.args.get('min_score', 3))
        rules     = _extract_rules(book['text'], min_score=min_score)
        _book_store[book_id]['rules'] = rules
        grouped   = {}
        for rule in rules:
            for cat in rule['categories']:
                grouped.setdefault(cat, []).append(rule)
        return jsonify({'book_id': book_id, 'filename': book['filename'],
                        'total_rules': len(rules),
                        'by_category': {cat: len(r) for cat, r in grouped.items()},
                        'top_rules': rules[:50], 'all_rules': rules[:200]})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── API: Delete Book ──────────────────────────────────────────────────────────
@app.route('/api/books/<book_id>', methods=['DELETE'])
def api_delete_book(book_id):
    try:
        if book_id not in _book_store:
            return jsonify({'error': 'Book not found'}), 404
        book = _book_store.pop(book_id)
        try: os.remove(book['save_path'])
        except Exception: pass
        return jsonify({'deleted': book_id, 'filename': book['filename']})
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

# ── New page routes ───────────────────────────────────────────────────────────
@app.route('/interpret')
def interpret_page():
    return render_template('interpret.html')

@app.route('/pdf-toolkit')
def pdf_toolkit_page():
    return render_template('pdf_toolkit.html')

@app.route('/learning')
def learning_page():
    return render_template('learning.html')

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static',    exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
