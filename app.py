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
DASHA_YEARS_BY_ID  = [6, 10, 7, 17, 16, 20, 19, 18, 7]  # Sun..Ketu  (120 yr)
SHAD_BALA_LABELS   = ['Sthana','Dig','Kala','Chesta','Naisargika','Drik',
                       'Total Rupa','Required','Ratio']
SHAD_BALA_PLANETS  = ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn']

RASI_SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
               'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

# Sign lords (traditional Vedic)
SIGN_LORDS = {
    'Aries':'Mars','Taurus':'Venus','Gemini':'Mercury','Cancer':'Moon',
    'Leo':'Sun','Virgo':'Mercury','Libra':'Venus','Scorpio':'Mars',
    'Sagittarius':'Jupiter','Capricorn':'Saturn','Aquarius':'Saturn','Pisces':'Jupiter',
}

# Planetary dignities
EXALTATION_SIGN = {
    'Sun':'Aries','Moon':'Taurus','Mars':'Capricorn','Mercury':'Virgo',
    'Jupiter':'Cancer','Venus':'Pisces','Saturn':'Libra',
    'Rahu':'Gemini','Ketu':'Sagittarius',
}
DEBILITATION_SIGN = {
    'Sun':'Libra','Moon':'Scorpio','Mars':'Cancer','Mercury':'Pisces',
    'Jupiter':'Capricorn','Venus':'Virgo','Saturn':'Aries',
    'Rahu':'Sagittarius','Ketu':'Gemini',
}
OWN_SIGNS = {
    'Sun':['Leo'],'Moon':['Cancer'],'Mars':['Aries','Scorpio'],
    'Mercury':['Gemini','Virgo'],'Jupiter':['Sagittarius','Pisces'],
    'Venus':['Taurus','Libra'],'Saturn':['Capricorn','Aquarius'],
}
MOOLATRIKONA = {
    'Sun':'Leo','Moon':'Taurus','Mars':'Aries','Mercury':'Virgo',
    'Jupiter':'Sagittarius','Venus':'Libra','Saturn':'Aquarius',
}

# Nakshatras
NAKSHATRA_NAMES = [
    'Ashwini','Bharani','Krittika','Rohini','Mrigashira','Ardra',
    'Punarvasu','Pushya','Ashlesha','Magha','Purva Phalguni','Uttara Phalguni',
    'Hasta','Chitra','Swati','Vishakha','Anuradha','Jyeshtha',
    'Mula','Purva Ashadha','Uttara Ashadha','Shravana','Dhanishtha',
    'Shatabhisha','Purva Bhadrapada','Uttara Bhadrapada','Revati',
]
NAKSHATRA_LORDS = (
    ['Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury'] * 3
)

# House significations
HOUSE_KARKA = {
    1: 'Self, body, vitality, personality, appearance',
    2: 'Wealth, family, speech, food, face, right eye',
    3: 'Courage, siblings, short travel, communication, arms, desire',
    4: 'Mother, home, property, happiness, vehicles, chest, education',
    5: 'Children, intelligence, past-life merit, speculation, creativity, stomach',
    6: 'Enemies, disease, debts, service, litigation, waist',
    7: 'Spouse, marriage, partnerships, business, foreign travel, groin',
    8: 'Longevity, inheritance, transformation, occult, hidden matters, accidents',
    9: 'Father, dharma, luck, religion, guru, higher education, thighs',
    10:'Career, fame, authority, action, public life, status, knees',
    11:'Gains, income, elder siblings, social network, desires, ankles',
    12:'Loss, liberation, foreign lands, spirituality, bed pleasures, left eye',
}
KENDRA_HOUSES  = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES= {6, 8, 12}
UPACHAYA_HOUSES= {3, 6, 10, 11}

# Special planetary aspects (beyond universal 7th aspect)
SPECIAL_ASPECTS = {
    'Mars':   [4, 8],
    'Jupiter':[5, 9],
    'Saturn': [3, 10],
    'Rahu':   [5, 9],
    'Ketu':   [5, 9],
}

# Expanded keyword set for rule scoring
ASTRO_KEYWORDS = {
    'planets':   ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu',
                  'surya','chandra','mangal','budha','guru','shukra','shani'],
    'signs':     ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra',
                  'Scorpio','Sagittarius','Capricorn','Aquarius','Pisces',
                  'mesha','vrishabha','mithuna','karka','simha','kanya',
                  'tula','vrischika','dhanu','makara','kumbha','meena'],
    'yoga':      ['yoga','dosha','conjunction','aspect','exalted','debilitated',
                  'retrograde','kendra','trikona','trine','dharma','karma',
                  'raja','dhana','neecha','uccha','mool','vargottama',
                  'parivartana','exchange','gajakesari','mahapurusha'],
    'house':     ['house','bhava','lagna','ascendant','lord','sthana','kshetra',
                  'dusthana','upachaya','kendra','angle','succedent','trikonas'],
    'dasha':     ['dasha','mahadasha','antardasha','bhukti','period','transit',
                  'vimsottari','pratyantara','antaradasha'],
    'predict':   ['gives','causes','results','indicates','shows','produces',
                  'brings','native','person','born','will','bestows','confers',
                  'grants','makes','renders','likely','prone','suffers','enjoys'],
    'nakshatra': ['nakshatra','star','pada','asterism','lunar','mansion'],
    'quality':   ['benefic','malefic','natural','functional','exaltation','debilitation',
                  'moolatrikona','own sign','friendly','enemy','neecha bhanga','dig bala'],
}

# Compiled regex formula patterns for structured rule extraction
_PLANETS_RE = r'(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)'
_SIGNS_RE   = r'(?:Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)'
_HOUSE_RE   = r'(\d+)(?:st|nd|rd|th)?'

FORMULA_PATTERNS = [
    # planet in sign: "Jupiter in Cancer"
    (re.compile(rf'({_PLANETS_RE})\s+in\s+({_SIGNS_RE})', re.I),
     'planet_in_sign', ('planet','sign')),
    # planet in house: "Mercury in the 10th house / bhava"
    (re.compile(rf'({_PLANETS_RE})\s+(?:in|placed\s+in|posited\s+in|occupies?)\s+(?:the\s+)?{_HOUSE_RE}\s*(?:house|bhava|from)?', re.I),
     'planet_in_house', ('planet','house')),
    # lord of X in Y: "lord of 5th in 9th"
    (re.compile(r'lord\s+of\s+(?:the\s+)?' + _HOUSE_RE + r'\s*(?:house|bhava)?\s+(?:in|placed|posited)\s+(?:the\s+)?' + _HOUSE_RE, re.I),
     'lord_transfer', ('from_house','to_house')),
    # conjunction: "Mars and Jupiter" / "Venus with Moon"
    (re.compile(rf'({_PLANETS_RE})\s+(?:and|with|conjunct[s]?|combined?\s+with)\s+({_PLANETS_RE})', re.I),
     'conjunction', ('planet1','planet2')),
    # aspect: "Saturn aspects Jupiter" / "Jupiter aspecting Mars"
    (re.compile(rf'({_PLANETS_RE})\s+(?:aspects?|aspecting)\s+({_PLANETS_RE})', re.I),
     'aspect', ('aspector','aspected')),
    # exalted: "Sun exalted" / "exalted Jupiter"
    (re.compile(rf'(?:({_PLANETS_RE})\s+(?:exalted|uccha|in\s+exaltation)|(?:exalted|uccha)\s+({_PLANETS_RE}))', re.I),
     'exaltation', ('planet','planet_alt')),
    # debilitated: "Moon debilitated" / "neecha Saturn"
    (re.compile(rf'(?:({_PLANETS_RE})\s+(?:debilitated|neecha|in\s+debilitation)|(?:debilitated|neecha)\s+({_PLANETS_RE}))', re.I),
     'debilitation', ('planet','planet_alt')),
    # retrograde
    (re.compile(rf'(?:retrograde|vakri)\s+({_PLANETS_RE})', re.I),
     'retrograde', ('planet',)),
    # yoga name: "Gaja Kesari Yoga", "Raja Yoga"
    (re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+Yoga)', re.I),
     'yoga_name', ('name',)),
    # kendra/trikona placement
    (re.compile(rf'({_PLANETS_RE})\s+in\s+(?:kendra|trikona|dusthana|upachaya|angle|trine)', re.I),
     'special_house_type', ('planet',)),
]

# ── Planet natural significations ────────────────────────────────────────────
PLANET_KARAKAS = {
    'Sun':     'soul, self, authority, vitality, father, career in leadership, government recognition',
    'Moon':    'mind, emotions, mother, public reputation, fluids, sensitivity, memory, intuition',
    'Mars':    'courage, energy, siblings, real estate, passion, conflict, surgery, blood, ambition',
    'Mercury': 'intelligence, communication, trade, education, writing, analysis, friends, skill',
    'Jupiter': 'wisdom, dharma, children, guru, wealth expansion, husband (for women), liver, grace',
    'Venus':   'love, wife (for men), arts, vehicles, luxury, beauty, pleasure, sensual comforts',
    'Saturn':  'discipline, longevity, delays, servants, chronic labor, bones, isolation, karmic lessons',
    'Rahu':    'foreign elements, obsession, unconventional paths, illusion, sudden disruptions, ambition',
    'Ketu':    'spirituality, liberation, past life karma, renunciation, detachment, sharp intuition',
}

# ── Life area → primary houses ───────────────────────────────────────────────
LIFE_AREA_HOUSES = {
    'career':       [10, 6, 2, 11],
    'marriage':     [7, 2, 11, 8],
    'wealth':       [2, 11, 5, 9],
    'health':       [1, 6, 8, 12],
    'children':     [5, 9],
    'education':    [4, 5, 9],
    'travel':       [3, 9, 12],
    'property':     [4, 2],
    'spirituality': [9, 12, 8],
    'mother':       [4, 2],
    'father':       [9, 10],
    'siblings':     [3, 11],
    'enemies':      [6, 12],
    'longevity':    [8, 1],
    'creativity':   [5, 1, 3],
    'social':       [11, 3, 7],
    'foreign':      [12, 9, 3],
    'relationship': [7, 11, 5],
}

# ── Life area keyword detection ───────────────────────────────────────────────
LIFE_AREA_KEYWORDS = {
    'career':       ['career','job','work','profession','business','promotion','success','status','occupation','10th','vocation'],
    'marriage':     ['marriage','spouse','wife','husband','relationship','partner','wedding','love','7th','divorce','marry','matrimony'],
    'wealth':       ['money','wealth','income','finance','rich','savings','investment','earn','2nd','11th','debt','poor','financial'],
    'health':       ['health','disease','illness','sick','hospital','surgery','body','fitness','medicine','6th','pain','recover'],
    'children':     ['children','child','son','daughter','kids','fertility','5th','baby','pregnancy','progeny'],
    'education':    ['education','study','college','degree','school','learning','graduation','knowledge','university','course'],
    'travel':       ['travel','foreign','abroad','immigration','trip','journey','12th','9th','settle','emigrate','overseas'],
    'property':     ['property','house','home','land','real estate','apartment','4th','vehicle','car','asset'],
    'spirituality': ['spiritual','moksha','liberation','religion','faith','god','meditation','astrology','guru','temple'],
    'mother':       ['mother','mom','maternal','4th'],
    'father':       ['father','dad','paternal','9th'],
    'siblings':     ['brother','sister','sibling','3rd'],
    'enemies':      ['enemy','enemies','opposition','competition','rival','legal','court','lawsuit','litigation'],
    'longevity':    ['longevity','lifespan','death','legacy','inheritance','8th','accident','crisis'],
    'creativity':   ['creativity','art','music','dance','writing','talent','hobby','performance','creative'],
    'social':       ['friends','network','social','community','11th','group','organization','society'],
    'foreign':      ['foreign','abroad','immigration','settle','overseas','international','outside'],
    'relationship': ['relationship','love','partner','companion','dating','romance','romantic'],
}

# ── Built-in classical rules (always available, no PDF upload required) ───────
# Sourced from Brihat Parashara Hora Shastra, Phaladeepika, and divisional chart
# research principles. Each rule is matched by the formula engine against the chart.
BUILTIN_RULES = [
    # ── EXALTATION RULES ──────────────────────────────────────────────────────
    {'text': 'The Sun placed in Aries reaches its highest exaltation, bestowing exceptional leadership, vitality, and a commanding presence. The native carries natural authority and tends to rise in positions of power.',
     'score': 9, 'categories': ['dignity','lagna'], 'planets': ['Sun'], 'signs': ['Aries'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Sun','sign':'Aries'},{'type':'exaltation','planet':'Sun'}]},
    {'text': 'The Moon in Taurus reaches its peak of exaltation, producing exceptional emotional stability, a fertile mind, and deep contentment. These natives are grounded, sensuous, and materially fortunate.',
     'score': 9, 'categories': ['dignity'], 'planets': ['Moon'], 'signs': ['Taurus'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Moon','sign':'Taurus'},{'type':'exaltation','planet':'Moon'}]},
    {'text': 'Mars exalted in Capricorn bestows exceptional drive, strategic execution, and disciplined ambition. The native achieves through sustained effort, often excelling in technical, military, or administrative fields.',
     'score': 9, 'categories': ['dignity','career'], 'planets': ['Mars'], 'signs': ['Capricorn'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mars','sign':'Capricorn'},{'type':'exaltation','planet':'Mars'}]},
    {'text': 'Mercury in Virgo is in both its own sign and exaltation — the highest expression of analytical intelligence. These natives possess exceptional precision, mastery of language, and outstanding reasoning abilities.',
     'score': 10, 'categories': ['dignity','education'], 'planets': ['Mercury'], 'signs': ['Virgo'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mercury','sign':'Virgo'},{'type':'exaltation','planet':'Mercury'}]},
    {'text': 'Jupiter exalted in Cancer is a supreme blessing — wisdom, grace, and prosperity flow naturally. The native receives abundant blessings in family life, education, and spiritual wisdom. This placement protects the entire chart.',
     'score': 10, 'categories': ['dignity','wealth','spirituality'], 'planets': ['Jupiter'], 'signs': ['Cancer'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Jupiter','sign':'Cancer'},{'type':'exaltation','planet':'Jupiter'}]},
    {'text': 'Venus in Pisces reaches its highest exaltation, producing extraordinary artistic gifts, refined sensibilities, and deeply harmonious relationships. These natives bring beauty wherever they go.',
     'score': 9, 'categories': ['dignity','marriage','creativity'], 'planets': ['Venus'], 'signs': ['Pisces'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Venus','sign':'Pisces'},{'type':'exaltation','planet':'Venus'}]},
    {'text': 'Saturn exalted in Libra brings exceptionally disciplined judgment and a rare capacity for fair governance. The native earns authority through sustained effort and becomes a pillar of justice in their field.',
     'score': 9, 'categories': ['dignity','career'], 'planets': ['Saturn'], 'signs': ['Libra'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Saturn','sign':'Libra'},{'type':'exaltation','planet':'Saturn'}]},
    # ── DEBILITATION RULES ────────────────────────────────────────────────────
    {'text': 'The Sun in Libra loses its natural authority — ego and self-assertion become areas of struggle. The native may feel overshadowed or find it difficult to command recognition, especially in early life.',
     'score': 8, 'categories': ['dignity'], 'planets': ['Sun'], 'signs': ['Libra'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Sun','sign':'Libra'},{'type':'debilitation','planet':'Sun'}]},
    {'text': 'Moon in Scorpio in debilitation creates emotional turbulence and intense psychological depth. The mind moves through cycles of transformation; trust comes slowly, and early life may carry emotional wounds that ultimately become sources of great wisdom.',
     'score': 8, 'categories': ['dignity','health'], 'planets': ['Moon'], 'signs': ['Scorpio'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Moon','sign':'Scorpio'},{'type':'debilitation','planet':'Moon'}]},
    {'text': 'Mars in Cancer is debilitated — drive and aggression become internalized. Energy direction requires conscious channeling. Creative, domestic, or nurturing applications of Mars energy yield the best results.',
     'score': 7, 'categories': ['dignity'], 'planets': ['Mars'], 'signs': ['Cancer'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mars','sign':'Cancer'},{'type':'debilitation','planet':'Mars'}]},
    {'text': 'Mercury in Pisces is debilitated — sharp logical analysis gives way to intuitive, impressionistic thinking. The native may be imaginative and compassionate but benefits from structured intellectual disciplines.',
     'score': 7, 'categories': ['dignity','education'], 'planets': ['Mercury'], 'signs': ['Pisces'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mercury','sign':'Pisces'},{'type':'debilitation','planet':'Mercury'}]},
    {'text': 'Jupiter in Capricorn is in debilitation — wisdom meets material resistance. Traditional expansion and optimism are channeled into structured worldly ambition. Financial wisdom develops slowly but eventually becomes solid and lasting.',
     'score': 7, 'categories': ['dignity','wealth'], 'planets': ['Jupiter'], 'signs': ['Capricorn'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Jupiter','sign':'Capricorn'},{'type':'debilitation','planet':'Jupiter'}]},
    {'text': 'Venus in Virgo is debilitated — love and art face critical analysis. The native may set impossibly high standards in relationships, leading to disappointment. Accepting imperfection transforms this into refined discernment.',
     'score': 7, 'categories': ['dignity','marriage'], 'planets': ['Venus'], 'signs': ['Virgo'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Venus','sign':'Virgo'},{'type':'debilitation','planet':'Venus'}]},
    {'text': 'Saturn in Aries in debilitation creates friction between discipline and impulse. The native must consciously cultivate patience. Hard work eventually brings recognition once the impulsive Aries energy is harnessed by Saturnine structure.',
     'score': 7, 'categories': ['dignity'], 'planets': ['Saturn'], 'signs': ['Aries'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Saturn','sign':'Aries'},{'type':'debilitation','planet':'Saturn'}]},
    # ── PLANET IN HOUSE ───────────────────────────────────────────────────────
    {'text': 'Sun placed in the 1st house gives a magnetic, authoritative personality. The native radiates solar energy, often becoming a natural leader. Health is generally robust and the ego is well-defined. There is a deep drive to be recognized and respected.',
     'score': 8, 'categories': ['planet','lagna'], 'planets': ['Sun'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':1}]},
    {'text': 'Sun in the 10th house brings exceptional career prominence, fame, and authority. These natives achieve leadership in their chosen field. Government, administration, and public recognition come naturally.',
     'score': 9, 'categories': ['planet','career'], 'planets': ['Sun'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':10},{'type':'special_house_type','planet':'Sun','house_type':'kendra'}]},
    {'text': 'Sun in the 5th house brings brilliance, creative intelligence, and a deep love of learning. Leadership in educational or creative institutions comes naturally. The relationship with children or students is a source of great pride.',
     'score': 7, 'categories': ['planet','education','children'], 'planets': ['Sun'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':5}]},
    {'text': 'Moon in the 4th house is in its most natural and powerful position. Emotional security, domestic happiness, and a strong bond with the mother are hallmarks. The native finds true peace at home and often has a fine instinct for real estate.',
     'score': 9, 'categories': ['planet','property'], 'planets': ['Moon'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':4}]},
    {'text': 'Moon in the 1st house creates a sensitive, empathic, and receptive personality. The mind is deeply connected to emotions and the body. Popularity comes naturally, as does a changeable nature. The relationship with the mother is central to identity.',
     'score': 7, 'categories': ['planet','lagna'], 'planets': ['Moon'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':1}]},
    {'text': 'Moon in the 7th house brings emotionally rich partnerships. The spouse is intuitive, nurturing, and sensitive. The native seeks emotional fulfillment through relationships, making marriage a central life theme.',
     'score': 7, 'categories': ['planet','marriage'], 'planets': ['Moon'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':7}]},
    {'text': 'Mars in the 10th house generates powerful career drive, competitive energy, and executive ability. These natives excel in military, police, surgery, engineering, sports, or any field requiring decisive action and courage.',
     'score': 8, 'categories': ['planet','career'], 'planets': ['Mars'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':10}]},
    {'text': 'Mars in the 6th house is a powerful indicator of victory over enemies, disease, and competition. The native has enormous physical stamina, excels in service-oriented careers, and wins legal battles. Immunity and competitive drive are exceptional.',
     'score': 8, 'categories': ['planet','health','career'], 'planets': ['Mars'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':6}]},
    {'text': 'Mars in the 7th house as a Mangal Dosha indicator creates intensity in partnerships. Relationships begin with great passion and require conscious effort to sustain. The spouse may be strong-willed and active. Energy directed wisely transforms partnerships.',
     'score': 8, 'categories': ['planet','marriage'], 'planets': ['Mars'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':7}]},
    {'text': 'Mars in the 1st house gives raw physical vitality, courage, and a pioneering spirit. The native is assertive, competitive, and driven. Leadership by action rather than words defines this placement.',
     'score': 7, 'categories': ['planet','lagna'], 'planets': ['Mars'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':1}]},
    {'text': 'Mercury in the 10th house favors careers in communication, business, accounting, writing, teaching, and technology. The native is intellectually sharp in professional matters and often advances through intelligence and articulation.',
     'score': 8, 'categories': ['planet','career','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':10}]},
    {'text': 'Mercury in the 1st house gives an exceptionally active, curious, and communicative personality. The native thinks quickly, speaks well, and processes information rapidly. Early education is important, and the mind remains youthful throughout life.',
     'score': 7, 'categories': ['planet','lagna','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':1}]},
    {'text': 'Mercury in the 5th house sharpens intelligence, creativity, and the capacity for study. Excellent for academics, authors, strategists, and teachers. Children are intellectually gifted. Speculative ventures benefit from analytical thinking.',
     'score': 8, 'categories': ['planet','education','children'], 'planets': ['Mercury'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':5}]},
    {'text': 'Jupiter in the 1st house is one of the most auspicious placements in the chart. It confers wisdom, an expansive worldview, a naturally fortunate disposition, and protection from adversity. The native commands natural respect and is often physically imposing.',
     'score': 10, 'categories': ['planet','lagna','wealth','spirituality'], 'planets': ['Jupiter'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':1},{'type':'special_house_type','planet':'Jupiter','house_type':'kendra'}]},
    {'text': 'Jupiter in the 5th house is a supreme blessing for children, intelligence, and past-life merit. Multiple children are indicated, and they tend to be exceptional. The mind is philosophical and creative. Investments often yield gains.',
     'score': 10, 'categories': ['planet','children','education','wealth'], 'planets': ['Jupiter'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':5},{'type':'special_house_type','planet':'Jupiter','house_type':'trikona'}]},
    {'text': 'Jupiter in the 7th house blesses the marriage partner with wisdom, abundance, and a generous spirit. The spouse tends to be educated, optimistic, and spiritually inclined. Marriage is generally fortunate and the native benefits greatly through partnerships.',
     'score': 9, 'categories': ['planet','marriage'], 'planets': ['Jupiter'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':7}]},
    {'text': 'Jupiter in the 9th house is in its most natural home. Dharma, higher learning, guru connections, and profound fortune are the hallmarks. The native is drawn to philosophy, law, or spirituality. Long-distance travel and foreign connections bring blessings.',
     'score': 10, 'categories': ['planet','spirituality','travel','wealth'], 'planets': ['Jupiter'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':9},{'type':'special_house_type','planet':'Jupiter','house_type':'trikona'}]},
    {'text': 'Jupiter in the 11th house brings abundant gains, a wide social network, and steady income that grows over time. Financial aspirations are fulfilled, especially in the second half of life. Elder siblings are a source of support.',
     'score': 9, 'categories': ['planet','wealth','social'], 'planets': ['Jupiter'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':11}]},
    {'text': 'Jupiter in the 4th house gives happiness at home, a wise and nurturing mother, and deep domestic contentment. The native has an instinctive love of learning, a well-appointed home, and is likely to acquire property.',
     'score': 8, 'categories': ['planet','property'], 'planets': ['Jupiter'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':4}]},
    {'text': 'Venus in the 7th house is its most natural domain for relationship matters. The spouse is likely to be attractive, artistic, and loving. Marriage brings happiness, and partnerships — personal and professional — are generally harmonious and productive.',
     'score': 9, 'categories': ['planet','marriage'], 'planets': ['Venus'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':7}]},
    {'text': 'Venus in the 2nd house brings wealth, a refined family background, and eloquent speech. The native has a natural appreciation for the finer things in life. Income often comes through beauty, arts, or luxury industries. Family life is harmonious.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Venus'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':2}]},
    {'text': 'Venus in the 10th house brings career success through beauty, arts, entertainment, fashion, luxury goods, or diplomacy. The native is well-liked by superiors and often achieves through charm and social grace.',
     'score': 8, 'categories': ['planet','career','creativity'], 'planets': ['Venus'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':10}]},
    {'text': 'Venus in the 1st house bestows physical attractiveness, charm, and a natural grace. The native has an artistic temperament, a love of pleasure, and tends to succeed through their personal magnetism and aesthetic sensibility.',
     'score': 7, 'categories': ['planet','lagna','creativity'], 'planets': ['Venus'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':1}]},
    {'text': 'Saturn in the 10th house is a classic indicator of a long, distinguished career. Initial delays and hard work define the early career, but sustained effort brings lasting recognition and authority. Government service, law, and management are favored.',
     'score': 9, 'categories': ['planet','career'], 'planets': ['Saturn'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':10},{'type':'special_house_type','planet':'Saturn','house_type':'kendra'}]},
    {'text': 'Saturn in the 8th house grants exceptional longevity and a deep interest in occult matters. Sudden events and transformations become catalysts for profound growth. Inheritance and hidden resources may benefit the native after midlife.',
     'score': 8, 'categories': ['planet','longevity','spirituality'], 'planets': ['Saturn'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':8}]},
    {'text': 'Saturn in the 7th house delays marriage and brings a serious, responsible partner. The spouse tends to be older or from a different background. Marriage, once established, is enduring. Business partnerships require careful legal structuring.',
     'score': 8, 'categories': ['planet','marriage'], 'planets': ['Saturn'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':7}]},
    {'text': 'Saturn in the 1st house creates a serious, disciplined, and often reserved personality. The native takes on responsibilities early, ages gracefully, and builds lasting achievements through methodical effort. Health requires attention in youth.',
     'score': 7, 'categories': ['planet','lagna'], 'planets': ['Saturn'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':1}]},
    {'text': 'Rahu in the 10th house creates a powerful drive for worldly success and recognition. The native pursues unconventional career paths with great ambition. Fame — including sudden or international recognition — is possible. Technology and foreign connections favor career.',
     'score': 8, 'categories': ['planet','career','foreign'], 'planets': ['Rahu'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':10}]},
    {'text': 'Rahu in the 7th house brings unconventional partnerships and an attraction to foreign or very different partners. Marriage has unusual elements and requires flexibility. International business partnerships can be highly lucrative.',
     'score': 7, 'categories': ['planet','marriage','foreign'], 'planets': ['Rahu'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':7}]},
    {'text': 'Rahu in the 12th house strongly indicates foreign settlement, international travel, and unusual spiritual experiences. The native may spend extended periods abroad. Hidden matters, research, and institutions play a significant role in life.',
     'score': 8, 'categories': ['planet','foreign','spirituality'], 'planets': ['Rahu'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':12}]},
    {'text': 'Rahu in the 1st house creates a personality of unusual magnetism, ambition, and a strong drive to reinvent oneself. The native often leads an unconventional life, crossing cultural or social boundaries to forge a unique identity.',
     'score': 7, 'categories': ['planet','lagna'], 'planets': ['Rahu'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':1}]},
    {'text': 'Ketu in the 9th house indicates deep past-life dharmic merit and a natural inclination toward spiritual liberation. The native may reject conventional religious forms in favor of a direct, inner path. Guru connections are karmic and transformative.',
     'score': 9, 'categories': ['planet','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':9}]},
    {'text': 'Ketu in the 1st house creates a spiritually oriented, somewhat detached personality with exceptional intuitive ability. These natives often seem otherworldly and carry a sense of karmic completion. Past-life skills surface effortlessly.',
     'score': 8, 'categories': ['planet','spirituality','lagna'], 'planets': ['Ketu'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':1}]},
    {'text': 'Ketu in the 5th house brings unusual intelligence, past-life learning, and a detached relationship with children. Spiritual practices connected to creativity are very powerful here. Academic pursuits may be unconventional but produce deep results.',
     'score': 7, 'categories': ['planet','spirituality','children'], 'planets': ['Ketu'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':5}]},
    # ── CONJUNCTION RULES ─────────────────────────────────────────────────────
    {'text': 'Jupiter and Venus in conjunction form a powerful wealth and wisdom combination. The native possesses both material prosperity and refined taste. Marriage is blessed, and creative or financial ventures flourish. This is one of the most auspicious planetary pairs.',
     'score': 9, 'categories': ['conjunction','wealth','marriage'], 'planets': ['Jupiter','Venus'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Jupiter','planet2':'Venus'}]},
    {'text': 'Jupiter and Mercury in conjunction create exceptional intellectual capacity, communication mastery, and wisdom. The native excels in teaching, law, writing, and philosophy. Learning comes easily and the mind ranges across multiple domains.',
     'score': 9, 'categories': ['conjunction','education'], 'planets': ['Jupiter','Mercury'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Jupiter','planet2':'Mercury'}]},
    {'text': 'Sun and Jupiter together create a Guru-Aditya combination — wisdom amplified by solar power. Leadership with ethical foundations, recognition in educational or spiritual fields, and a noble character are the natural expression of this union.',
     'score': 8, 'categories': ['conjunction','career','spirituality'], 'planets': ['Sun','Jupiter'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Sun','planet2':'Jupiter'}]},
    {'text': 'Saturn and Mars together create an intense, disciplined combination. When harmonized, this produces extraordinary stamina, technical excellence, and the ability to execute large projects. Engineering, military, and surgery are favored areas.',
     'score': 8, 'categories': ['conjunction','career'], 'planets': ['Saturn','Mars'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Saturn','planet2':'Mars'}]},
    {'text': 'Sun and Moon in conjunction (Amavasya) creates an intensely focused, self-contained personality. The conscious and subconscious minds operate as one unit. Emotions and will act together, making the native highly purposeful.',
     'score': 7, 'categories': ['conjunction','lagna'], 'planets': ['Sun','Moon'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Sun','planet2':'Moon'}]},
    {'text': 'Venus and Mercury together produce excellent communication around beauty, arts, and relationships. These natives have a natural gift for diplomacy, writing, and careers in media, design, counselling, and the performing arts.',
     'score': 7, 'categories': ['conjunction','creativity','career'], 'planets': ['Venus','Mercury'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Venus','planet2':'Mercury'}]},
    {'text': 'Moon and Jupiter in conjunction form the seed of Gaja Kesari Yoga — emotional wisdom, public popularity, and a generous, expansive disposition. The native tends to be well-regarded, emotionally balanced, and fortunate in domestic matters.',
     'score': 9, 'categories': ['conjunction','wealth','social'], 'planets': ['Moon','Jupiter'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Moon','planet2':'Jupiter'}]},
    {'text': 'Sun and Venus in conjunction creates a charming personality with artistic talent and social confidence. The native shines in creative fields and attracts recognition through beauty and eloquence. Relationships benefit from the solar warmth.',
     'score': 7, 'categories': ['conjunction','creativity','marriage'], 'planets': ['Sun','Venus'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Sun','planet2':'Venus'}]},
    {'text': 'Moon and Venus together create exceptional aesthetic sensitivity, emotional warmth, and an innate understanding of beauty. The native is deeply empathic in relationships and often has talent in music, poetry, or visual arts.',
     'score': 8, 'categories': ['conjunction','creativity','marriage'], 'planets': ['Moon','Venus'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Moon','planet2':'Venus'}]},
    # ── HOUSE LORD YOGA RULES ─────────────────────────────────────────────────
    {'text': 'When the lord of the 5th house is placed in the 9th house, or vice versa, a powerful Raja Yoga is formed. Intelligence, higher learning, children, and dharma all receive a tremendous boost. Exceptional fortune and wisdom characterize the life.',
     'score': 10, 'categories': ['yoga','wealth','children','spirituality'], 'planets': [], 'signs': [], 'houses': [5,9],
     'formulas': [{'type':'lord_transfer','from_house':5,'to_house':9}]},
    {'text': 'The lord of the 1st house placed in the 10th house, or the 10th lord in the 1st house, creates an exceptionally strong career yoga. The native\'s identity and career purpose are aligned. Professional rise, public prominence, and a strong sense of vocation result.',
     'score': 9, 'categories': ['yoga','career'], 'planets': [], 'signs': [], 'houses': [1,10],
     'formulas': [{'type':'lord_transfer','from_house':1,'to_house':10}]},
    {'text': 'The 7th lord placed in the 7th house is a significant indicator of a stable, long-lasting marriage. The partner is loyal and prominent, and the marriage relationship is a major source of fulfillment. Business partnerships are also marked by equality and longevity.',
     'score': 8, 'categories': ['house_lord','marriage'], 'planets': [], 'signs': [], 'houses': [7],
     'formulas': [{'type':'lord_transfer','from_house':7,'to_house':7}]},
    {'text': 'The 10th lord in the 10th house creates a powerful career yoga. Career is exceptional, highly focused, and the native typically reaches the pinnacle of their chosen profession. Authority, fame, and recognition come through sustained excellence.',
     'score': 9, 'categories': ['house_lord','career'], 'planets': [], 'signs': [], 'houses': [10],
     'formulas': [{'type':'lord_transfer','from_house':10,'to_house':10}]},
    {'text': 'When the 2nd and 11th lords are connected by conjunction, mutual aspect, or exchange, a potent Dhana Yoga is formed. Accumulated wealth grows steadily. Income streams multiply and financial goals are achieved in due time.',
     'score': 9, 'categories': ['house_lord','wealth'], 'planets': [], 'signs': [], 'houses': [2,11],
     'formulas': [{'type':'lord_transfer','from_house':2,'to_house':11}]},
    {'text': 'The 9th lord placed in the 1st house brings extraordinary good fortune directly into the personality. The native is blessed from birth with luck, wisdom, and a righteous disposition. Travel, higher learning, and spiritual connections come naturally.',
     'score': 9, 'categories': ['house_lord','wealth','spirituality'], 'planets': [], 'signs': [], 'houses': [9,1],
     'formulas': [{'type':'lord_transfer','from_house':9,'to_house':1}]},
    {'text': 'The 5th lord placed in the 1st house connects intelligence and fortune directly to the personality. Intelligence is a major asset. Creative endeavors succeed. Children are a source of pride and joy.',
     'score': 9, 'categories': ['house_lord','children','education'], 'planets': [], 'signs': [], 'houses': [5,1],
     'formulas': [{'type':'lord_transfer','from_house':5,'to_house':1}]},
    {'text': 'The Lagna lord placed in the 9th house brings profound luck, philosophical wisdom, and a lifelong connection to dharmic activities. Fortune operates through the native\'s own initiative, and long journeys prove exceptionally fruitful.',
     'score': 9, 'categories': ['house_lord','spirituality','travel'], 'planets': [], 'signs': [], 'houses': [1,9],
     'formulas': [{'type':'lord_transfer','from_house':1,'to_house':9}]},
    {'text': 'The Lagna lord in the 7th house, or the 7th lord in the 1st, creates a strong connection between the self and partnerships. Marriage and business relationships become defining life experiences and a primary vehicle for growth.',
     'score': 8, 'categories': ['house_lord','marriage'], 'planets': [], 'signs': [], 'houses': [1,7],
     'formulas': [{'type':'lord_transfer','from_house':1,'to_house':7}]},
    # ── SIGN-BASED OWN SIGN RULES ─────────────────────────────────────────────
    {'text': 'Jupiter in Sagittarius, its moolatrikona sign, is in its most philosophical and expansive expression. Teaching, law, religion, and long journeys are the natural domains. Optimism, generosity, and an unwavering faith in higher principles define the nature.',
     'score': 9, 'categories': ['planet','spirituality','education'], 'planets': ['Jupiter'], 'signs': ['Sagittarius'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Jupiter','sign':'Sagittarius'}]},
    {'text': 'Saturn in Capricorn, its moolatrikona sign, bestows tremendous organizational power, disciplined ambition, and a capacity for patient long-term achievement. These natives often reach the very top of hierarchical structures through sheer consistency.',
     'score': 8, 'categories': ['planet','career'], 'planets': ['Saturn'], 'signs': ['Capricorn'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Saturn','sign':'Capricorn'}]},
    {'text': 'Mars in Aries, its moolatrikona sign, expresses raw initiative, competitive drive, and pioneering energy at their finest. The native is a natural leader who acts decisively. Independence and direct action define the life path.',
     'score': 8, 'categories': ['planet','career'], 'planets': ['Mars'], 'signs': ['Aries'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mars','sign':'Aries'}]},
    {'text': 'The Sun in Leo, its own sign, shines with full confidence, creative power, and natural authority. The native is designed to lead, perform, and be seen. A strong sense of self-expression, pride in achievements, and a warm-hearted nature are hallmarks.',
     'score': 8, 'categories': ['planet','lagna','career'], 'planets': ['Sun'], 'signs': ['Leo'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Sun','sign':'Leo'}]},
    {'text': 'Moon in Cancer, its own sign, creates exceptional emotional depth, intuitive perception, and a powerful connection to home and family. The native has a natural healing presence and an instinctive understanding of human needs.',
     'score': 8, 'categories': ['planet','lagna'], 'planets': ['Moon'], 'signs': ['Cancer'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Moon','sign':'Cancer'}]},
    {'text': 'Venus in Taurus, its moolatrikona sign, expresses sensory refinement, material wealth, and stable love at their purest. The native has a deep love of nature, beauty, and music. Financial accumulation comes naturally through practical skill and aesthetic talent.',
     'score': 8, 'categories': ['planet','wealth','creativity'], 'planets': ['Venus'], 'signs': ['Taurus'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Venus','sign':'Taurus'}]},
    {'text': 'Mercury in Gemini, its moolatrikona sign, is the most fluid and communicative expression of Mercury. Quick wit, versatility, and an insatiable curiosity make the native adept in communication, trade, and the rapid exchange of ideas.',
     'score': 8, 'categories': ['planet','education','career'], 'planets': ['Mercury'], 'signs': ['Gemini'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mercury','sign':'Gemini'}]},
    # ── SPECIAL YOGA RULES ────────────────────────────────────────────────────
    {'text': 'When Jupiter is in a kendra from the Moon, the Gaja Kesari Yoga is formed — one of the most celebrated combinations in Jyotish. This yoga grants intelligence, eloquence, fame, wealth, and a life that endures in memory.',
     'score': 10, 'categories': ['yoga','wealth','social'], 'planets': ['Jupiter','Moon'], 'signs': [], 'houses': [],
     'formulas': [{'type':'yoga_name','name':'Gaja Kesari'},{'type':'special_house_type','planet':'Jupiter','house_type':'kendra'}]},
    {'text': 'Hamsa Yoga is formed when Jupiter occupies its own sign or exaltation in a kendra. This Pancha Mahapurusha Yoga bestows spiritual wisdom, a noble character, and recognition as a counselor of rare wisdom and grace.',
     'score': 10, 'categories': ['yoga','spirituality','wealth'], 'planets': ['Jupiter'], 'signs': ['Sagittarius','Pisces','Cancer'], 'houses': [1,4,7,10],
     'formulas': [{'type':'yoga_name','name':'Hamsa Yoga'},{'type':'special_house_type','planet':'Jupiter','house_type':'kendra'}]},
    {'text': 'Malavya Yoga arises when Venus occupies its own sign or exaltation in a kendra. This Pancha Mahapurusha Yoga grants sensual refinement, artistic brilliance, a beautiful form, luxury comforts, and a highly harmonious married life.',
     'score': 10, 'categories': ['yoga','marriage','creativity','wealth'], 'planets': ['Venus'], 'signs': ['Taurus','Libra','Pisces'], 'houses': [1,4,7,10],
     'formulas': [{'type':'yoga_name','name':'Malavya Yoga'},{'type':'special_house_type','planet':'Venus','house_type':'kendra'}]},
    {'text': 'Ruchaka Yoga forms when Mars occupies Aries, Scorpio, or Capricorn in a kendra. This Pancha Mahapurusha Yoga produces exceptional physical vitality, military prowess, decisive leadership, and the ability to overcome all opposition.',
     'score': 10, 'categories': ['yoga','career'], 'planets': ['Mars'], 'signs': ['Aries','Scorpio','Capricorn'], 'houses': [1,4,7,10],
     'formulas': [{'type':'yoga_name','name':'Ruchaka Yoga'},{'type':'special_house_type','planet':'Mars','house_type':'kendra'}]},
    {'text': 'Sasa Yoga arises when Saturn is in Capricorn, Aquarius, or Libra in a kendra. This Pancha Mahapurusha Yoga gives exceptional organizational ability, authority over masses, long-lasting professional success, and a commanding, disciplined nature.',
     'score': 10, 'categories': ['yoga','career'], 'planets': ['Saturn'], 'signs': ['Capricorn','Aquarius','Libra'], 'houses': [1,4,7,10],
     'formulas': [{'type':'yoga_name','name':'Sasa Yoga'},{'type':'special_house_type','planet':'Saturn','house_type':'kendra'}]},
    {'text': 'Bhadra Yoga is formed when Mercury is in Gemini or Virgo in a kendra. This Pancha Mahapurusha Yoga confers exceptional intellect, command of language, commercial acumen, and recognition as a master of knowledge and communication.',
     'score': 10, 'categories': ['yoga','education','career'], 'planets': ['Mercury'], 'signs': ['Gemini','Virgo'], 'houses': [1,4,7,10],
     'formulas': [{'type':'yoga_name','name':'Bhadra Yoga'},{'type':'special_house_type','planet':'Mercury','house_type':'kendra'}]},
    # ── ASPECT RULES ──────────────────────────────────────────────────────────
    {'text': 'Jupiter aspecting the Lagna or Lagna lord is one of the most protective influences in astrology. It elevates the entire life, brings wisdom to the personality, and ensures that even difficult periods are met with grace and ultimate resolution.',
     'score': 9, 'categories': ['yoga','lagna','wealth'], 'planets': ['Jupiter'], 'signs': [], 'houses': [1],
     'formulas': [{'type':'aspect','planet':'Jupiter','house':1}]},
    {'text': 'Jupiter\'s aspect on the 7th house blesses the marriage sphere with wisdom and optimism. The spouse tends to be generous and educated. Marriage is generally fortunate and the native benefits deeply through partnerships.',
     'score': 8, 'categories': ['marriage'], 'planets': ['Jupiter'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'aspect','planet':'Jupiter','house':7}]},
    {'text': 'Jupiter\'s aspect on the 5th house is one of the most auspicious combinations for intelligence, children, and creative endeavors. Wisdom flows into the 5th house significations, producing exceptional children and inspired creativity.',
     'score': 9, 'categories': ['children','education','creativity'], 'planets': ['Jupiter'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'aspect','planet':'Jupiter','house':5}]},
    {'text': 'Saturn\'s aspect on the 10th house instills career discipline, longevity of professional standing, and authority in public life. Though early struggles may appear, the native ultimately earns lasting recognition through sustained ethical conduct.',
     'score': 8, 'categories': ['career'], 'planets': ['Saturn'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'aspect','planet':'Saturn','house':10}]},
    {'text': 'Mars aspecting the 4th house brings intensity to domestic matters and can indicate property dealings, real estate investments, or a forceful mother. Engineering work on the home or land is also indicated.',
     'score': 6, 'categories': ['property'], 'planets': ['Mars'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'aspect','planet':'Mars','house':4}]},
    {'text': 'Mars aspecting the 7th house brings passion and competition into partnerships. The spouse may be energetic and strong-willed. Relationships benefit when this Mars energy is channeled into shared goals rather than conflict.',
     'score': 7, 'categories': ['marriage'], 'planets': ['Mars'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'aspect','planet':'Mars','house':7}]},
    # ── DIVISIONAL CHART PRINCIPLES (D9 marriage, D10 career, D7 children) ────
    {'text': 'A strong 7th house with well-placed Venus and an unafflicted 7th lord indicates that marriage is clearly promised by the chart. The Navamsha (D9) confirms the quality and timing. Benefic planets amplifying the 7th house bring marital joy.',
     'score': 8, 'categories': ['marriage'], 'planets': ['Venus'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':7}]},
    {'text': 'When benefic planets occupy the 7th house or aspect it without affliction, timely and happy marriage is indicated. Jupiter or Venus aspecting the 7th house in the birth chart is a particularly favorable combination for fulfilling marriage.',
     'score': 8, 'categories': ['marriage'], 'planets': ['Jupiter','Venus'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'aspect','planet':'Jupiter','house':7}]},
    {'text': 'When the 10th house lord is strong and placed in a kendra or trikona, and the 10th house receives benefic aspects, a distinguished career with societal recognition is promised. The quality of the Dashamsha (D10) reflects the specific domain of achievement.',
     'score': 8, 'categories': ['career'], 'planets': [], 'signs': [], 'houses': [10],
     'formulas': [{'type':'special_house_type','planet':'Saturn','house_type':'kendra'}]},
    {'text': 'A strong 5th house with Jupiter as significator and an unafflicted 5th lord indicates clear promise of children. The Saptamsha (D7) confirms the number and quality of children. Jupiter in the 5th is the single most favorable placement for happy, successful progeny.',
     'score': 9, 'categories': ['children'], 'planets': ['Jupiter'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':5}]},
    {'text': 'A well-placed 4th house lord with benefic influence on the 4th house indicates property ownership, happiness at home, and a comfortable domestic environment. A strong Moon further confirms these comforts. The Chaturthamsha (D4) shows the quality of fixed assets.',
     'score': 7, 'categories': ['property'], 'planets': ['Moon'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':4}]},
    {'text': 'The 12th house indicates foreign residence, especially when it is activated by Rahu, the 12th lord is strong, or the Lagna lord connects with the 12th. A strong 9th-12th axis with foreign planet connections confirms settlement abroad is possible.',
     'score': 7, 'categories': ['foreign','travel'], 'planets': ['Rahu'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':12}]},
    {'text': 'The 9th house is the house of fortune, dharma, and the father. When the 9th house lord is strong and in a favorable position, the native enjoys lasting good fortune, a righteous path, and a supportive relationship with the father figure.',
     'score': 8, 'categories': ['spirituality','wealth'], 'planets': [], 'signs': [], 'houses': [9],
     'formulas': [{'type':'lord_transfer','from_house':9,'to_house':1}]},
    {'text': 'The 2nd house represents accumulated wealth, family, and speech. When the 2nd lord is strongly placed and Jupiter aspects the 2nd house or its lord, the native accumulates significant wealth over time and comes from a supportive family background.',
     'score': 7, 'categories': ['wealth'], 'planets': ['Jupiter'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'aspect','planet':'Jupiter','house':2}]},
    {'text': 'Multiple planets in the 10th house create an exceptionally dynamic career. Each planet adds its significations to the professional domain. When benefics are included in this stellium, recognition, authority, and varied income sources follow.',
     'score': 8, 'categories': ['career'], 'planets': [], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':10}]},
    {'text': 'When both the Lagna lord and the Lagna are unafflicted, and the Lagna lord is placed in a kendra or trikona, the native enjoys excellent health, a strong constitution, and a life where vitality supports the pursuit of all other goals.',
     'score': 8, 'categories': ['health','lagna'], 'planets': [], 'signs': [], 'houses': [1],
     'formulas': [{'type':'special_house_type','planet':'Jupiter','house_type':'trikona'}]},

    # ══ COMPLETE PLANET-IN-HOUSE TABLE (all 9 planets × 12 houses) ════════════
    # ── SUN remaining houses ──────────────────────────────────────────────────
    {'text': 'Sun in the 2nd house brings strong family values, authority in speech, and a father-figure role in the family. Wealth is earned through effort and association with government or authority. Speech carries conviction. Dietary choices strongly affect health.',
     'score': 7, 'categories': ['planet','wealth'], 'planets': ['Sun'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':2}]},
    {'text': 'Sun in the 3rd house gives tremendous courage, initiative, and drive in communication. Siblings play a key role in life. The native is bold, competitive, and excels in short journeys, media, writing, and any field requiring initiative and bravery.',
     'score': 7, 'categories': ['planet','career'], 'planets': ['Sun'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':3}]},
    {'text': 'Sun in the 4th house can bring conflicts with the mother or difficulty with homeland, yet also grants significant property. The father may be absent or assertive. Public status and inner happiness evolve through resolving domestic tensions. Excellent for real estate.',
     'score': 7, 'categories': ['planet','property'], 'planets': ['Sun'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':4}]},
    {'text': 'Sun in the 6th house gives exceptional will to overcome enemies, disease, and competition. The native wins in litigation and service sectors. Health issues may arise but the Solar vitality eventually conquers. Government service is highly favored.',
     'score': 7, 'categories': ['planet','health','career'], 'planets': ['Sun'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':6}]},
    {'text': 'Sun in the 7th house creates tensions with the spouse or partners through ego clashes, yet the spouse is a person of status and capability. Business with government is profitable. Public dealings and trade with authority figures mark the career.',
     'score': 7, 'categories': ['planet','marriage'], 'planets': ['Sun'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':7}]},
    {'text': 'Sun in the 8th house creates hidden battles with authority and father-figures, possible health issues in mid-life, and a deep interest in occult, research, or inheritance matters. The native has a capacity for profound transformation and rebirth after crisis.',
     'score': 7, 'categories': ['planet','longevity','spirituality'], 'planets': ['Sun'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':8}]},
    {'text': 'Sun in the 9th house is exceptionally auspicious for fortune, father, and dharma. The native enjoys the blessings of a powerful, noble father figure. Higher education, law, and long journeys bring tremendous rewards. The life is inherently fortunate.',
     'score': 9, 'categories': ['planet','spirituality','wealth'], 'planets': ['Sun'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':9}]},
    {'text': 'Sun in the 11th house is one of the finest placements for income, aspirations, and social achievement. The native earns consistently through authority, government connections, or public roles. Elder siblings and influential networks are key assets.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Sun'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':11}]},
    {'text': 'Sun in the 12th house inclines the native toward foreign lands, spiritual retreats, and selfless service. Government or hospital work abroad is possible. The ego must learn to dissolve into service. There is a strong past-life connection to sacred institutions.',
     'score': 7, 'categories': ['planet','foreign','spirituality'], 'planets': ['Sun'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':12}]},
    # ── MOON remaining houses ─────────────────────────────────────────────────
    {'text': 'Moon in the 2nd house brings a wealthy, emotionally bonded family, sweet and fluid speech, and wealth that fluctuates with the mind. The native has an instinctive talent for accumulation. The relationship with the mother deeply shapes the voice and values.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Moon'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':2}]},
    {'text': 'Moon in the 3rd house creates a nurturing, communicative, and emotionally expressive relationship with siblings. The native is imaginative, creative in writing or media, and emotionally driven in their courage. Frequent short journeys characterize the life.',
     'score': 7, 'categories': ['planet','career'], 'planets': ['Moon'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':3}]},
    {'text': 'Moon in the 5th house creates a deeply intuitive, imaginative, and emotionally creative intelligence. Children are especially beloved. The native has a natural gift for storytelling, teaching, and creative arts. Emotional fulfillment comes through creative expression.',
     'score': 8, 'categories': ['planet','children','creativity'], 'planets': ['Moon'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':5}]},
    {'text': 'Moon in the 6th house creates fluctuating health tied to emotional states. Service, healthcare, and healing are natural vocations. The native has strong emotional resilience in adversity and an empathic ability to serve others in need.',
     'score': 6, 'categories': ['planet','health'], 'planets': ['Moon'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':6}]},
    {'text': 'Moon in the 8th house creates emotional intensity, deep psychic perception, and a life shaped by transformative events. The native is drawn to occult sciences, psychology, and hidden truths. Inheritance or legacy matters are common life themes.',
     'score': 7, 'categories': ['planet','longevity','spirituality'], 'planets': ['Moon'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':8}]},
    {'text': 'Moon in the 9th house blesses the native with a deeply devotional nature, a loving and wise mother, and fortune from birth. Long pilgrimages, deep respect for gurus, and an intuitive grasp of dharmic truths define the life.',
     'score': 9, 'categories': ['planet','spirituality','wealth'], 'planets': ['Moon'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':9}]},
    {'text': 'Moon in the 10th house brings exceptional public visibility, popularity, and a career tied to the public mood. Business, politics, entertainment, and any people-facing role flourishes. The mother may be a powerful career influence or public figure herself.',
     'score': 9, 'categories': ['planet','career'], 'planets': ['Moon'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':10}]},
    {'text': 'Moon in the 11th house gives an emotionally driven social network, gains through women and the public, and a nurturing approach to friendships. Income fluctuates but generally grows. The mother and elder siblings are allies in life goals.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Moon'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':11}]},
    {'text': 'Moon in the 12th house gives a deeply psychic and introspective nature, love of solitude, and a connection to foreign lands or spiritual institutions. The native is drawn to meditation, hospital work, or any form of behind-the-scenes service. Overseas life is possible.',
     'score': 7, 'categories': ['planet','foreign','spirituality'], 'planets': ['Moon'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':12}]},
    # ── MARS remaining houses ─────────────────────────────────────────────────
    {'text': 'Mars in the 2nd house creates forceful, direct speech — sometimes harsh. Family conflicts around money or authority are common early in life. Wealth is earned through physical or competitive work. The voice is powerful and the appetite is strong.',
     'score': 6, 'categories': ['planet','wealth'], 'planets': ['Mars'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':2}]},
    {'text': 'Mars in the 3rd house is exceptionally powerful — it gives courage, athletic ability, competitive strength, and excellent relations with bold siblings. The native is decisive in communication and thrives in fields requiring physical or mental initiative.',
     'score': 9, 'categories': ['planet','career'], 'planets': ['Mars'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':3}]},
    {'text': 'Mars in the 4th house as Mangal Dosha on the domestic house creates property disputes, mother-related tensions, and domestic intensity. Real estate investments, engineering of the home, and forceful domestic management are indicated. Land acquisition is strong.',
     'score': 6, 'categories': ['planet','property'], 'planets': ['Mars'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':4}]},
    {'text': 'Mars in the 5th house brings passionate, competitive intelligence and intense connection to creative projects and children. Academic performance can be exceptional when channelled properly. The native is driven in speculative ventures and sports.',
     'score': 7, 'categories': ['planet','children','education'], 'planets': ['Mars'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':5}]},
    {'text': 'Mars in the 8th house is the planet of war in the house of transformation — creating the potential for accidents, surgeries, and crises that ultimately forge a warrior spirit. Long life comes through surviving intense tests. Occult research and military service are favored.',
     'score': 7, 'categories': ['planet','longevity'], 'planets': ['Mars'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':8}]},
    {'text': 'Mars in the 9th house creates an independent, assertive approach to dharma that may conflict with conventional religious institutions. The native carves their own philosophical path. Foreign journeys are undertaken with zeal. Conflict with the father is possible.',
     'score': 6, 'categories': ['planet','spirituality','travel'], 'planets': ['Mars'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':9}]},
    {'text': 'Mars in the 11th house drives competitive, ambitious accumulation of wealth and a forceful social network. The native wins income through competition, sports, or entrepreneurship. Elder siblings and allies are energetic and competitive allies in goals.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Mars'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':11}]},
    {'text': 'Mars in the 12th house creates hidden adversaries, potential for foreign conflicts, and expenses through impulsive action. Yet it also grants tremendous capacity for behind-the-scenes executive work, foreign service, hospital management, or military postings abroad.',
     'score': 6, 'categories': ['planet','foreign'], 'planets': ['Mars'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':12}]},
    # ── MERCURY remaining houses ──────────────────────────────────────────────
    {'text': 'Mercury in the 2nd house blesses speech with precision, eloquence, and commercial acuity. The native accumulates wealth through intellect, writing, trade, and communication skills. The family background is educated and articulate. Financial intelligence is exceptional.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Mercury'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':2}]},
    {'text': 'Mercury in the 3rd house is its natural domain — this placement bestows exceptional writing, communication, and intellectual agility. The native excels in journalism, publishing, marketing, and all forms of information dissemination. Siblings share intellectual bonds.',
     'score': 9, 'categories': ['planet','career','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':3}]},
    {'text': 'Mercury in the 4th house creates an intellectually rich home environment, an educated mother, and a love of learning from domestic and traditional sources. The native is skilled at real estate transactions and benefits from the family\'s accumulated knowledge.',
     'score': 7, 'categories': ['planet','property','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':4}]},
    {'text': 'Mercury in the 6th house gives an analytical, service-oriented mind — excellent for medicine, accounting, legal aid, research, and data analysis. The native methodically solves problems and wins through intelligent service. Health improves through dietary attention.',
     'score': 7, 'categories': ['planet','health','career'], 'planets': ['Mercury'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':6}]},
    {'text': 'Mercury in the 7th house brings an intellectual spouse who communicates openly and thinks analytically. Business partnerships with intelligent, articulate partners are favorable. Legal agreements, contracts, and commercial negotiations are areas of strength.',
     'score': 7, 'categories': ['planet','marriage','career'], 'planets': ['Mercury'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':7}]},
    {'text': 'Mercury in the 8th house grants a deep, research-oriented mind inclined toward occult sciences, psychology, and hidden knowledge. The native makes an excellent investigator, researcher, healer, or esoteric scholar. Writing about hidden subjects is productive.',
     'score': 7, 'categories': ['planet','spirituality','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':8}]},
    {'text': 'Mercury in the 9th house creates a philosophical, teaching, and publishing orientation. The native is drawn to higher education, law, and international intellectual discourse. Writing books of lasting philosophical value is strongly indicated. Multiple degrees are common.',
     'score': 8, 'categories': ['planet','spirituality','education'], 'planets': ['Mercury'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':9}]},
    {'text': 'Mercury in the 11th house brings consistent gains through intelligence, writing, and networks of intellectual peers. The native earns through communication, trading, and technology. Multiple income streams generated through mental work are characteristic.',
     'score': 8, 'categories': ['planet','wealth'], 'planets': ['Mercury'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':11}]},
    {'text': 'Mercury in the 12th house creates a meditative, introspective mind that finds expression in foreign lands or solitary research. The native excels in writing about spiritual or psychological subjects. Work in foreign countries or with foreign language is common.',
     'score': 7, 'categories': ['planet','foreign','spirituality'], 'planets': ['Mercury'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':12}]},
    # ── JUPITER remaining houses ──────────────────────────────────────────────
    {'text': 'Jupiter in the 2nd house (2nd being the house of wealth) creates a highly auspicious financial environment — the family is prosperous, speech is wise and inspiring, and the native accumulates wealth over time. Multiple income streams through teaching or counseling are indicated.',
     'score': 9, 'categories': ['planet','wealth'], 'planets': ['Jupiter'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':2}]},
    {'text': 'Jupiter in the 3rd house blesses siblings with wisdom and creates an interest in philosophical writing and teaching through communication. The native is a teacher through their words and short journeys. Religious writings and philosophical content flow naturally.',
     'score': 7, 'categories': ['planet','spirituality','education'], 'planets': ['Jupiter'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':3}]},
    {'text': 'Jupiter in the 6th house is a powerful indicator of victory over enemies, disease, and competition — through wisdom rather than force. The native triumphs in legal disputes and heals through knowledge. Service in law, medicine, or spiritual counseling is indicated.',
     'score': 8, 'categories': ['planet','health','career'], 'planets': ['Jupiter'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':6}]},
    {'text': 'Jupiter in the 8th house grants a deep interest in occult wisdom, philosophical research, and the mysteries of life and death. The native has a long life protected by Jupiter\'s benefic nature. Sudden inheritance or hidden wealth may appear during Jupiter\'s dasha.',
     'score': 8, 'categories': ['planet','longevity','spirituality'], 'planets': ['Jupiter'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':8}]},
    {'text': 'Jupiter in the 10th house creates a distinguished career in teaching, law, finance, religion, or administration. The native commands natural authority and is respected for wisdom. This is the placement of the judge, professor, or high counsel.',
     'score': 9, 'categories': ['planet','career'], 'planets': ['Jupiter'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':10}]},
    {'text': 'Jupiter in the 12th house creates a deeply spiritual nature, connection to ashrams, monasteries, or foreign sacred spaces. The native may live and serve abroad. Moksha and liberation are strongly indicated in this lifetime. Spiritual study brings lasting fulfillment.',
     'score': 8, 'categories': ['planet','foreign','spirituality'], 'planets': ['Jupiter'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':12}]},
    # ── VENUS remaining houses ────────────────────────────────────────────────
    {'text': 'Venus in the 3rd house brings artistic flair to communication, a beautiful speaking voice, and artistic or musical siblings. The native expresses love through creative channels. Short journeys for artistic pursuits or pleasure are characteristic.',
     'score': 7, 'categories': ['planet','creativity'], 'planets': ['Venus'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':3}]},
    {'text': 'Venus in the 4th house creates a beautiful, harmonious home environment with luxurious comforts. The mother is loving and aesthetically refined. The native has excellent taste in home décor, property investment, and domestic pleasures. Real estate brings comfort.',
     'score': 8, 'categories': ['planet','property'], 'planets': ['Venus'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':4}]},
    {'text': 'Venus in the 5th house blesses creative intelligence with artistic and romantic depth. The native excels in performance arts, design, and any creative field. Children are beautiful and artistically gifted. Romance is a central and joyful life theme.',
     'score': 8, 'categories': ['planet','creativity','children'], 'planets': ['Venus'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':5}]},
    {'text': 'Venus in the 6th house can indicate a service-oriented relationship with beauty — working in wellness, hospitality, fashion, or healthcare. Workplace relationships may be romantic or harmonious. Health issues may arise through over-indulgence in pleasure.',
     'score': 6, 'categories': ['planet','health','career'], 'planets': ['Venus'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':6}]},
    {'text': 'Venus in the 8th house gives magnetic allure through mystery and transformation. The native has an interest in tantric arts, hidden beauty, and occult aesthetics. Joint finances with a spouse or partner may be a key wealth vehicle. Transformative relationships are catalytic.',
     'score': 7, 'categories': ['planet','marriage','spirituality'], 'planets': ['Venus'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':8}]},
    {'text': 'Venus in the 9th house creates divine grace, a love of sacred aesthetics, and an affinity for beautiful religious or philosophical traditions. The native may marry someone foreign or of a different culture. Long-distance journeys for pleasure and culture are favored.',
     'score': 8, 'categories': ['planet','spirituality','travel'], 'planets': ['Venus'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':9}]},
    {'text': 'Venus in the 11th house brings gains through beauty, arts, and social connections. The native has an extensive, harmonious social network. Income from creative work, luxury goods, or entertainment is steady. Friendships with artistic people enrich the life.',
     'score': 8, 'categories': ['planet','wealth','creativity'], 'planets': ['Venus'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':11}]},
    {'text': 'Venus in the 12th house creates a love of hidden pleasures, private romance, and spiritual devotion to beauty. The native may have a connection to foreign arts, luxury retreats, or spiritual aesthetics. There is a deep inner richness to the sensory and spiritual life.',
     'score': 7, 'categories': ['planet','foreign','spirituality'], 'planets': ['Venus'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':12}]},
    # ── SATURN remaining houses ───────────────────────────────────────────────
    {'text': 'Saturn in the 2nd house delays the accumulation of family wealth and creates early financial struggle, but ultimately produces a disciplined, careful approach to finances that builds lasting security in the second half of life. Speech is measured and authoritative.',
     'score': 6, 'categories': ['planet','wealth'], 'planets': ['Saturn'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':2}]},
    {'text': 'Saturn in the 3rd house creates persistence, sustained effort in communication, and a disciplined relationship with siblings. The native becomes an expert through hard work rather than natural talent. Technical writing, engineering communication, and systematic skill-building are favored.',
     'score': 7, 'categories': ['planet','career'], 'planets': ['Saturn'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':3}]},
    {'text': 'Saturn in the 4th house restricts early domestic happiness, may indicate a difficult mother relationship or property challenges early in life. However, Saturn in the 4th ultimately builds real estate wealth through systematic effort. Late-life domestic peace is achieved through hard work.',
     'score': 6, 'categories': ['planet','property'], 'planets': ['Saturn'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':4}]},
    {'text': 'Saturn in the 5th house limits children or delays having them, and creates a disciplined, structured approach to learning and creativity. Education is earned through sustained effort. Intelligence is profound but deliberate rather than spontaneous.',
     'score': 6, 'categories': ['planet','children','education'], 'planets': ['Saturn'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':5}]},
    {'text': 'Saturn in the 6th house is a powerful placement for overcoming enemies and disease through sustained effort and discipline. The native wins in litigation and service through perseverance. Chronic health issues eventually come under control through systematic management.',
     'score': 8, 'categories': ['planet','health','career'], 'planets': ['Saturn'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':6}]},
    {'text': 'Saturn in the 9th house creates a serious, conservative approach to dharma and a long, careful relationship with philosophy, law, and father figures. Formal religious structures appeal to the native. Fortune comes through sustained ethical conduct rather than luck.',
     'score': 7, 'categories': ['planet','spirituality'], 'planets': ['Saturn'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':9}]},
    {'text': 'Saturn in the 11th house is one of the finest placements for long-term financial gains. Wealth accumulates slowly and surely, reaching its peak in the second half of life. The social network is disciplined, professional, and built on genuine long-term relationships.',
     'score': 9, 'categories': ['planet','wealth'], 'planets': ['Saturn'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':11}]},
    {'text': 'Saturn in the 12th house creates a karmic pull toward solitude, ashrams, foreign service, and spiritual liberation. The native may work in institutions, jails, or hospitals. Foreign settlement is possible. There is a deep past-life orientation toward renunciation and inner freedom.',
     'score': 7, 'categories': ['planet','foreign','spirituality'], 'planets': ['Saturn'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':12}]},
    # ── RAHU remaining houses ─────────────────────────────────────────────────
    {'text': 'Rahu in the 2nd house creates an obsessive drive for wealth and accumulation, often through unconventional or foreign sources. Speech may be clever but deceptive at times. Foreign foods and unusual dietary habits are indicated. Family background may have mixed or foreign elements.',
     'score': 7, 'categories': ['planet','wealth','foreign'], 'planets': ['Rahu'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':2}]},
    {'text': 'Rahu in the 3rd house gives bold, unconventional communication and a fearless attitude toward self-promotion. The native is a natural risk-taker in media, technology, or travel. Siblings may be foreign-born or very different in character. Courage amplified by obsession.',
     'score': 7, 'categories': ['planet','career'], 'planets': ['Rahu'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':3}]},
    {'text': 'Rahu in the 4th house creates an unusual domestic environment — the home may be in a foreign country, or the mother may be unconventional. Property matters have unusual twists. Foreign real estate or unconventional living arrangements are common life features.',
     'score': 6, 'categories': ['planet','property','foreign'], 'planets': ['Rahu'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':4}]},
    {'text': 'Rahu in the 5th house creates unconventional intelligence, unusual creative expression, and a complex relationship with children. The native may have an adopted or step-child, or children of mixed heritage. Speculative ventures have amplified risk and reward.',
     'score': 6, 'categories': ['planet','children','creativity'], 'planets': ['Rahu'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':5}]},
    {'text': 'Rahu in the 6th house is one of the best placements for Rahu — it creates an obsessive drive to defeat enemies, overcome disease, and dominate competition. The native may rise dramatically in service, law, or medicine. Enemies are overcome through strategy and stamina.',
     'score': 9, 'categories': ['planet','career','health'], 'planets': ['Rahu'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':6}]},
    {'text': 'Rahu in the 8th house creates a deep obsession with occult, psychology, tantra, and the hidden dimensions of existence. Sudden transformative events shake the life periodically. Research in taboo or unconventional fields yields surprising insights.',
     'score': 7, 'categories': ['planet','spirituality','longevity'], 'planets': ['Rahu'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':8}]},
    {'text': 'Rahu in the 9th house creates an unconventional approach to dharma, foreign spiritual traditions, and self-made philosophy. The native may be drawn to unusual or foreign religions. Father figures may be absent or unconventional. Long foreign journeys are characteristic.',
     'score': 7, 'categories': ['planet','spirituality','travel'], 'planets': ['Rahu'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':9}]},
    {'text': 'Rahu in the 11th house is the most powerful placement for wealth and gain. The native accumulates resources obsessively and builds an extensive, international social network. Gains come from technology, foreign sources, and unconventional ventures. Wealth aspirations are sky-high.',
     'score': 10, 'categories': ['planet','wealth'], 'planets': ['Rahu'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Rahu','house':11}]},
    # ── KETU remaining houses ─────────────────────────────────────────────────
    {'text': 'Ketu in the 2nd house creates detachment from family wealth and material accumulation. The native may inherit spiritual rather than material wealth. Speech is direct and sometimes cutting. Past-life financial karma is being resolved, leading to spiritual renunciation of material desires.',
     'score': 6, 'categories': ['planet','wealth','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':2}]},
    {'text': 'Ketu in the 3rd house creates a detached, introspective approach to communication and a past-life relationship with siblings. The native may lose interest in conventional media and prefer deep, solitary study. Intuitive rather than logical communication is the strength.',
     'score': 6, 'categories': ['planet','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':3}]},
    {'text': 'Ketu in the 4th house creates detachment from the homeland and mother, often leading to settlement away from birth origin. The native searches for home in the spiritual realm. Past-life domestic karma must be resolved before inner peace can take root.',
     'score': 6, 'categories': ['planet','property','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':4}]},
    {'text': 'Ketu in the 6th house dissolves enemies — they disappear or are overcome without effort. Karmic healing of health issues occurs naturally. Service and healing from past-life wisdom emerge effortlessly. The native has an unusual immunity built from karmic strength.',
     'score': 8, 'categories': ['planet','health','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [6],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':6}]},
    {'text': 'Ketu in the 7th house creates a detached, spiritually oriented approach to partnerships. The native may marry a spiritual or otherworldly partner, or may prefer solitude to conventional partnership. Past-life partnership karma must be completed in this lifetime.',
     'score': 7, 'categories': ['planet','marriage','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':7}]},
    {'text': 'Ketu in the 8th house grants exceptional occult mastery, deep intuition into the mysteries of death and transformation, and a fearless approach to the unknown. Liberation through intense spiritual practice is strongly indicated. Longevity is protected by karmic grace.',
     'score': 9, 'categories': ['planet','spirituality','longevity'], 'planets': ['Ketu'], 'signs': [], 'houses': [8],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':8}]},
    {'text': 'Ketu in the 10th house creates a detached, unconventional career path. The native may frequently change professions or refuse conventional career structures. There is past-life mastery of worldly affairs, making career matters seemingly effortless yet also unimportant to the inner self.',
     'score': 7, 'categories': ['planet','career','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':10}]},
    {'text': 'Ketu in the 11th house creates a detached attitude toward gains and social networks — past-life wealth karma is strong, and material gains may come easily but feel hollow. The native is drawn to spiritual communities rather than commercial ones.',
     'score': 7, 'categories': ['planet','wealth','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [11],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':11}]},
    {'text': 'Ketu in the 12th house is the premier moksha indicator in Jyotish. The native is in the final stages of the spiritual journey, naturally inclined to liberation, meditation, and dissolution of the ego. Foreign spiritual practice, ashrams, and solitary retreat define the soul\'s direction.',
     'score': 10, 'categories': ['planet','spirituality'], 'planets': ['Ketu'], 'signs': [], 'houses': [12],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':12}]},

    # ══ KRISHNA KUMAR — SECRET OF VARGAS: DIVISIONAL CHART PRINCIPLES ═════════
    {'text': 'The foundational law of Divisional Charts (Vargas): any planet occupying its own sign in a divisional chart gains exceptional strength in that chart\'s specific life domain — for example, Jupiter in Sagittarius in the D-9 Navamsha greatly strengthens marriage and spiritual life simultaneously. Without examining divisional chart positions, prediction of specific life events is incomplete.',
     'score': 9, 'categories': ['yoga','spirituality'], 'planets': ['Jupiter'], 'signs': ['Sagittarius'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Jupiter','sign':'Sagittarius'}]},
    {'text': 'D-2 Hora Chart (Wealth Division): The Sun hora covers masculine signs (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius) and indicates wealth through authority, father, government, and self-earned income. The Moon hora covers feminine signs (Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces) and indicates wealth through maternal lineage, liquid assets, public, and inheritance. Planets in the stronger hora at birth time the primary wealth source.',
     'score': 8, 'categories': ['wealth'], 'planets': ['Sun','Moon'], 'signs': [], 'houses': [2],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':2}]},
    {'text': 'D-3 Drekkana Chart (Siblings and Courage): The condition of the 3rd house lord in the Drekkana chart shows the quality of sibling relationships and the native\'s courage. The 1st Drekkana (0-10°) carries the sign\'s own energy; the 2nd Drekkana (10-20°) takes the 5th sign\'s energy; the 3rd Drekkana (20-30°) takes the 9th sign\'s energy. Mars and Sun in the 1st Drekkana of a sign give extraordinary courage and initiative.',
     'score': 7, 'categories': ['career'], 'planets': ['Mars'], 'signs': [], 'houses': [3],
     'formulas': [{'type':'planet_in_house','planet':'Mars','house':3}]},
    {'text': 'D-4 Chaturthamsha Chart (Property and Domestic Fortune): A strong 4th lord in the D-4 Chaturthamsha indicates happiness from property, vehicles, and domestic comforts. Planets occupying their own sign or exaltation in D-4 confirm real estate gains. D-4 9th or 12th house activated by malefics can indicate settlement in a foreign country or far from birth origin.',
     'score': 7, 'categories': ['property'], 'planets': ['Moon'], 'signs': [], 'houses': [4],
     'formulas': [{'type':'planet_in_house','planet':'Moon','house':4}]},
    {'text': 'D-7 Saptamsha Chart (Children and Progeny): The condition of Jupiter (natural significator of children) and the 5th lord in the Saptamsha determines the quality, number, and timing of children. Jupiter in own sign or exaltation in D-7 gives wise, successful children. Malefics in D-7 5th house delay or restrict progeny. The rasi sign of D-7 Lagna lord indicates the sex of the first child (odd sign = male, even sign = female).',
     'score': 8, 'categories': ['children'], 'planets': ['Jupiter'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':5}]},
    {'text': 'D-9 Navamsha Chart (Marriage, Spouse Quality, and Soul Dharma): The Navamsha is the single most important divisional chart after the birth chart. The 7th house in D-9 shows spouse quality; an exalted or own-sign planet in the D-9 7th house promises an exceptional, supportive partner. The Navamsha Lagna represents the soul\'s deeper dharmic purpose. Vargottama planets (same sign in D-1 and D-9) are doubly strong and deliver exceptional results. The Atmakaraka planet placed in the D-9 Lagna indicates the highest fulfilment of the life purpose.',
     'score': 10, 'categories': ['marriage','spirituality'], 'planets': ['Venus'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':7}]},
    {'text': 'D-10 Dashamsha Chart (Career, Status, and Public Achievement): The quality and placement of the 10th lord and Sun in D-10 reveal the domain and height of career achievement. The Sun in D-10 indicates government, authority, and public roles; Saturn in D-10 indicates systematic, long-term organizational careers; Mercury in D-10 indicates intellectual or commercial achievement; Jupiter in D-10 indicates law, teaching, or spiritual leadership. Planets in kendra in D-10 confirm prominent career outcomes.',
     'score': 9, 'categories': ['career'], 'planets': ['Sun'], 'signs': [], 'houses': [10],
     'formulas': [{'type':'planet_in_house','planet':'Sun','house':10}]},
    {'text': 'D-12 Dwadashamsha Chart (Parental Blessings and Ancestral Karma): The condition of the Sun and 9th lord in D-12 shows paternal blessings and father\'s social status. The condition of the Moon and 4th lord in D-12 shows maternal blessings, mother\'s wellbeing, and quality of emotional nurturing received in childhood. Jupiter in D-12 indicates wise, educated parents of higher social standing.',
     'score': 7, 'categories': ['spirituality'], 'planets': ['Jupiter'], 'signs': [], 'houses': [9],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':9}]},
    {'text': 'D-16 Shodashamsha Chart (Vehicles and Domestic Comforts): Venus in its own sign or exaltation in D-16 gives luxury vehicles and fine domestic comforts. Saturn in D-16 indicates practical, durable but austere vehicles. The D-16 reflects both physical transport and the general quality of sensory comforts in life.',
     'score': 6, 'categories': ['property','wealth'], 'planets': ['Venus'], 'signs': ['Taurus','Libra','Pisces'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Venus','sign':'Taurus'}]},
    {'text': 'D-20 Vimshamsha Chart (Spiritual Practice and Liberation): A strong 9th or 12th house in D-20, especially occupied by Jupiter, Saturn, or Ketu, indicates significant spiritual progress in this lifetime. Ketu in D-20 Lagna or 12th house is the most powerful indicator that the soul is approaching moksha — liberation from the cycle of rebirth.',
     'score': 8, 'categories': ['spirituality'], 'planets': ['Ketu','Jupiter'], 'signs': [], 'houses': [9,12],
     'formulas': [{'type':'planet_in_house','planet':'Ketu','house':12}]},
    {'text': 'D-24 Chaturvimshamsha Chart (Education and Learning): A strong 5th lord and Mercury in D-24 indicate the level and quality of formal education. Jupiter in D-24 kendra confirms higher education, multiple degrees, or scholarly distinction. Mercury in its own sign in D-24 shows a natural scholar. This chart is studied for academic success and the depth of intellectual cultivation.',
     'score': 7, 'categories': ['education'], 'planets': ['Mercury','Jupiter'], 'signs': [], 'houses': [5],
     'formulas': [{'type':'planet_in_house','planet':'Mercury','house':5}]},
    {'text': 'D-30 Trimshamsha Chart (Evils, Health, and Karmic Challenges): Malefics in the D-30 Lagna or its lord in dusthana indicate significant health challenges, accidents, or karmic burdens in the life. Benefics in D-30 provide protection and spiritual resilience against these challenges. This chart is consulted when assessing serious health challenges, accidents, or karmic burdens.',
     'score': 7, 'categories': ['health'], 'planets': ['Saturn'], 'signs': [], 'houses': [1,6,8,12],
     'formulas': [{'type':'planet_in_house','planet':'Saturn','house':6}]},
    {'text': 'D-60 Shastiamsha (Karmic Soul Quality): The most microscopic divisional chart, D-60 reveals the soul\'s karmic quality at a highly refined level. Benefic D-60 positions indicate auspicious past-life karma; malefic positions reveal karmic debts requiring resolution in this life. Parashara prescribed this chart primarily for timing through dasha to verify the quality of each planetary period.',
     'score': 8, 'categories': ['spirituality'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},

    # ══ M.N. KEDAR — DELINEATION & DYNAMIC CONFIGURATION ═════════════════════
    {'text': 'Nakshatra-Lord Inheritance Principle (Kedar): A planet positioned in a nakshatra inherits the qualities and responsibilities of the nakshatra lord, and the effect is further coloured by the sign containing that nakshatra. For example, Mars in Ardra nakshatra (Rahu-ruled, in Mercury\'s sign Gemini) takes on Rahu\'s amplified, unconventional quality expressed through Gemini\'s intellectual domain — creating bold, unconventional communication and thinking.',
     'score': 9, 'categories': ['nakshatra'], 'planets': ['Mars'], 'signs': ['Gemini'], 'houses': [],
     'formulas': [{'type':'planet_in_sign','planet':'Mars','sign':'Gemini'}]},
    {'text': 'PAC Principle (Position, Aspect, Conjunction — Kedar): All astrological analysis must consider three types of planetary connections: Position (a planet directly placed in a house), Aspect (a planet casting its glance on a house), and Conjunction (planets occupying the same house). A planet with all three types of PAC connections to a key house makes that house a central, dominant theme of the life. Any prediction must reference at least one PAC connection for reliability.',
     'score': 9, 'categories': ['yoga'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Avastha (Planetary Maturity States) — Kedar: Planets have five avasthas based on degree within a sign: Bala (0-6°, infant — immature results, slow to manifest), Kumara (6-12°, youth — developing, partial results), Yuva (12-18°, mature adult — full strength, optimal manifestation), Vriddha (18-24°, old — declining, results waning), Mrita (24-30°, dead — dormant, results severely delayed or denied). A vargottama planet in Bala avastha needs careful interpretation — strong positionally but immature in delivery.',
     'score': 9, 'categories': ['dignity'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Vargottama Strength (Kedar & Krishna Kumar): A planet is Vargottama when it occupies the same sign in the birth chart (D-1) and the Navamsha (D-9). This creates a doubled, stable, anchored expression of the planet\'s nature. Vargottama planets are treated as exceptionally strong — even a debilitated planet that is vargottama gains considerable strength and delivers its results with unusual stability and predictability across all life areas it governs.',
     'score': 10, 'categories': ['dignity'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Rashi Sandhi Warning (Kedar): A planet placed in the last degree of a sign (especially 29°-30°) is in Rashi Sandhi — it stands at the junction of two signs and its energy is split and confused. Such a planet cannot deliver its significations clearly. Results of Rashi Sandhi planets are erratic, delayed, or expressed with unusual ambiguity. This vulnerability intensifies during that planet\'s own dasha period.',
     'score': 8, 'categories': ['dignity'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Nakshatra-lord chain: Moon in Jupiter\'s nakshatra (Punarvasu, Vishakha, or Purva Bhadrapada) inherits Jupiter\'s expansive, philosophical wisdom. The mind (Moon) naturally inclines toward dharma, higher learning, and optimistic world-view. This person finds emotional peace through study, teaching, and spiritual understanding, and typically attracts Guru-figures as key life-shapers.',
     'score': 8, 'categories': ['nakshatra','spirituality'], 'planets': ['Moon','Jupiter'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Moon','planet2':'Jupiter'}]},
    {'text': 'Nakshatra-lord chain: Moon in Saturn\'s nakshatra (Pushya, Anuradha, or Uttara Bhadrapada) gives the mind a Saturnine discipline, emotional depth, and capacity to endure hardship with equanimity. This person finds emotional security through structure, responsibility, and long-term commitments rather than immediate pleasures.',
     'score': 7, 'categories': ['nakshatra'], 'planets': ['Moon','Saturn'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Moon','planet2':'Saturn'}]},
    {'text': 'Nakshatra-lord chain: Mars in Rahu\'s nakshatra (Ardra, Swati, or Shatabhisha) amplifies Mars\'s already dynamic energy with Rahu\'s expansive obsession and unconventional drive. The native is bold, technically oriented, fascinated by cutting-edge fields, and driven by an intense, almost compulsive need to achieve and conquer. Foreign environments and technology amplify this energy.',
     'score': 8, 'categories': ['nakshatra','career'], 'planets': ['Mars','Rahu'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Mars','planet2':'Rahu'}]},
    {'text': 'Nakshatra-lord chain: Jupiter in Venus\'s nakshatra (Bharani, Purva Phalguni, or Purva Ashadha) blends Jupiter\'s wisdom and expansion with Venus\'s love of beauty and refined pleasure. This creates a person whose philosophy is expressed through beauty, art, and relationship — a natural teacher of aesthetics, law of attraction, and harmonious social principles.',
     'score': 8, 'categories': ['nakshatra','spirituality'], 'planets': ['Jupiter','Venus'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Jupiter','planet2':'Venus'}]},
    {'text': 'Nakshatra-lord chain: Sun in Rahu\'s nakshatra (Ardra, Swati, or Shatabhisha) creates an unconventional solar expression — the native\'s identity (Sun) is shaped by Rahu\'s desire to break conventions, achieve through unusual means, and connect to foreign or technological realms. Authority is sought through innovation rather than tradition.',
     'score': 7, 'categories': ['nakshatra'], 'planets': ['Sun','Rahu'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Sun','planet2':'Rahu'}]},
    {'text': 'Dynamic Configuration Principle (Kedar): For accurate prediction, the planets and houses in the birth chart must be cross-referenced with the relevant divisional chart AND the current Vimshottari Dasha lord. Only when all three layers confirm an event — birth chart, divisional chart, and dasha — should a prediction be considered reliable. A promise in the birth chart can only fructify during the appropriate dasha period.',
     'score': 10, 'categories': ['dasha'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},

    # ══ N.N. SHARMA — INTERPRETING DIVISIONAL CHARTS (K.N. Rao School) ════════
    {'text': 'Three-Point Verification Principle (K.N. Rao via N.N. Sharma): Every reliable astrological prediction must be confirmed by at least three houses, three planets, and two divisional charts working in unison. Single-planet or single-house analysis is insufficient for accurate prediction. Collective confirmation across multiple chart layers raises prediction accuracy dramatically — from ~65% to ~90%.',
     'score': 10, 'categories': ['yoga'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Divisional Charts as Microscopic Life Lenses (N.N. Sharma): Each divisional chart provides a microscopic, high-resolution view of a specific facet of life. The birth chart gives the overall picture; divisional charts zoom into one specific dimension — marriage, career, children, education, spirituality — with extraordinary precision. Ignoring divisional charts produces only surface-level predictions.',
     'score': 9, 'categories': ['yoga'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Navamsha — The Soul\'s Second Body (N.N. Sharma & K.N. Rao): The Navamsha chart is the soul\'s inner chart. The birth chart shows external circumstances; the Navamsha reveals the inner quality, spiritual depth, and ultimate direction of life. For marriage specifically, the Navamsha confirms not just whether marriage occurs, but the quality of the inner bond — whether it deepens the soul or creates spiritual dissonance.',
     'score': 10, 'categories': ['marriage','spirituality'], 'planets': ['Venus'], 'signs': [], 'houses': [7],
     'formulas': [{'type':'planet_in_house','planet':'Venus','house':7}]},
    {'text': 'Prarabdha and Planetary Dasha (N.N. Sharma): The birth chart contains both positive and negative promises (yogas and doshas). These promises can only fructify when the appropriate Vimshottari dasha lord activates them. A native with a powerful Raja Yoga may spend years in ordinary circumstances if their dasha sequence does not activate the yoga at the right age. The Dasha sequence determines WHEN karma manifests, not whether it exists.',
     'score': 10, 'categories': ['dasha'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},
    {'text': 'Sookhsham Chart Principle (N.N. Sharma): For extreme precision in timing — especially when two charts appear nearly identical (as with twins born minutes apart) — the Sookhsham (ultra-micro) divisional charts reveal the finest karmic distinctions. The same birth chart with a different dasha sequence produces a different life; combined with different Sookhsham positions, the destinies diverge completely, confirming karma\'s precision at the moment of birth.',
     'score': 8, 'categories': ['dasha'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': []},

    # ══ ADDITIONAL CLASSICAL YOGAS (Parashari & Saravali traditions) ════════
    {'text': 'Neecha Bhanga Raja Yoga: When a planet is debilitated (neecha), if the lord of the sign of debilitation or the lord of the sign of exaltation of the debilitated planet is in a kendra from Lagna or from the Moon, the debilitation is cancelled. This cancellation transforms the weakness into exceptional strength — producing outstanding results in the area the planet governs, typically in the second half of life after initial struggle.',
     'score': 10, 'categories': ['yoga','dignity'], 'planets': [], 'signs': [], 'houses': [1,4,7,10],
     'formulas': [{'type':'special_house_type','planet':'Moon','house_type':'kendra'}]},
    {'text': 'Viparita Raja Yoga: When the lord of the 6th, 8th, or 12th house is placed in any other dusthana (6th, 8th, or 12th), and is not conjunct or aspected by benefics, this forms the Viparita Raja Yoga — one of the most surprising and powerful yogas. It produces unexpected, sudden rise in status, wealth, or power — often through the misfortune or downfall of adversaries. Results come through apparent loss or adversity.',
     'score': 10, 'categories': ['yoga','wealth','career'], 'planets': [], 'signs': [], 'houses': [6,8,12],
     'formulas': [{'type':'special_house_type','planet':'Saturn','house_type':'dusthana'}]},
    {'text': 'Chandra-Mangala Yoga: When the Moon and Mars are in conjunction, mutual aspect, or exchange of signs, this Chandra-Mangala Yoga forms. The combination of emotional drive (Moon) and physical initiative (Mars) produces exceptional wealth-generating capacity, strong determination, and the ability to convert emotional momentum into tangible achievement. Business and trade ventures especially benefit.',
     'score': 8, 'categories': ['yoga','wealth'], 'planets': ['Moon','Mars'], 'signs': [], 'houses': [],
     'formulas': [{'type':'conjunction','planet1':'Moon','planet2':'Mars'}]},
    {'text': 'Adhi Yoga: When benefic planets (Mercury, Venus, Jupiter) occupy the 6th, 7th, and 8th houses from the Moon in any combination, Adhi Yoga forms. This gives the native the qualities of a minister, commander, or highly influential public figure — physical wellbeing, wealth, fame, and the capacity to lead and inspire others. Even partial formation (two of three) grants significant elevation.',
     'score': 9, 'categories': ['yoga','career','wealth'], 'planets': ['Mercury','Venus','Jupiter'], 'signs': [], 'houses': [6,7,8],
     'formulas': [{'type':'planet_in_house','planet':'Jupiter','house':6}]},
    {'text': 'Kahala Yoga: When the lords of the 4th and 9th houses are in mutual kendra positions (quadrant to each other), and the Lagna lord is strong, Kahala Yoga forms. This produces a fearless, persistent, tenacious character with extraordinary determination. The native is stubborn in the best sense — unwilling to be moved by opposition or adversity.',
     'score': 8, 'categories': ['yoga','career'], 'planets': [], 'signs': [], 'houses': [4,9],
     'formulas': [{'type':'lord_transfer','from_house':4,'to_house':10}]},
    {'text': 'Saraswati Yoga: When Mercury, Jupiter, and Venus are placed in kendras, trikonas, or the 2nd house from Lagna, Saraswati Yoga forms. This grants exceptional intellectual brilliance, artistic genius, command of multiple disciplines, and recognition as a scholar, artist, or person of extraordinary refinement and creative talent. The native becomes an authority in their chosen intellectual or artistic domain.',
     'score': 9, 'categories': ['yoga','education','creativity'], 'planets': ['Mercury','Jupiter','Venus'], 'signs': [], 'houses': [1,2,4,5,7,9,10],
     'formulas': [{'type':'conjunction','planet1':'Jupiter','planet2':'Mercury'}]},
    {'text': 'Lakshmi Yoga: When the Lagna lord is in its own sign or exaltation in a kendra, and the 9th lord is also in its own sign or exaltation in a kendra or trikona, Lakshmi Yoga forms. This is the yoga of Goddess Lakshmi — indicating exceptional wealth, luxurious living, a virtuous character, and a life marked by beauty, prosperity, and public respect. Marriage and family life are especially blessed.',
     'score': 10, 'categories': ['yoga','wealth'], 'planets': [], 'signs': [], 'houses': [1,9],
     'formulas': [{'type':'lord_transfer','from_house':9,'to_house':1}]},
    {'text': 'Kesari Yoga (Gajakesari variant): Jupiter placed in a kendra from the Moon sign creates this foundational prosperity yoga. The native has excellent judgment, emotional wisdom, generosity of spirit, and natural authority. Fame comes to the native organically, and the life is remembered with dignity. Financial stability and social respect are the hallmarks.',
     'score': 9, 'categories': ['yoga','wealth','social'], 'planets': ['Jupiter','Moon'], 'signs': [], 'houses': [],
     'formulas': [{'type':'special_house_type','planet':'Jupiter','house_type':'kendra'}]},
    {'text': 'Dhana Yogas through 5th and 9th lords: When the 5th lord and 9th lord combine by conjunction, aspect, or exchange — together with the 2nd and 11th lords — an exceptionally powerful wealth yoga forms that brings multiple income streams, accumulated assets, and financial fortune across the entire lifetime. Activation occurs during the dasha of any of these lords.',
     'score': 9, 'categories': ['yoga','wealth'], 'planets': [], 'signs': [], 'houses': [5,9,2,11],
     'formulas': [{'type':'lord_transfer','from_house':5,'to_house':9}]},
    {'text': 'Partial Pancha Mahapurusha Yoga: When a planet occupies its own or exaltation sign but in a neutral house (not a kendra), the Pancha Mahapurusha Yoga is partially formed. The native enjoys the quality of that planet\'s highest expression in personal character, but the public recognition associated with the full yoga (kendra placement) is diminished. The planet\'s dasha still delivers exceptional personal results.',
     'score': 7, 'categories': ['yoga'], 'planets': [], 'signs': [], 'houses': [1,4,7,10],
     'formulas': [{'type':'special_house_type','planet':'Jupiter','house_type':'kendra'}]},
    {'text': 'Lord of 1st, 5th, and 9th united (Triple Trikona Raja Yoga): When the lords of the 1st, 5th, and 9th houses form any combination — conjunction, aspect, or exchange — an extraordinarily powerful Raja Yoga results. All three trikonas unite, creating a life that is genuinely blessed across all domains: health, intelligence, wealth, dharma, and spiritual liberation.',
     'score': 10, 'categories': ['yoga','wealth','spirituality'], 'planets': [], 'signs': [], 'houses': [1,5,9],
     'formulas': [{'type':'lord_transfer','from_house':1,'to_house':5}]},
    {'text': 'House Lord in Own House (Swakshetra Bhava): Any house whose lord sits in that very same house creates a self-powered, self-sufficient energy in that life domain. The lord sitting in its own house does not depend on external support — it generates results from its own strength. This placement is especially powerful for the 1st, 7th, 10th, and 9th houses, creating strong independent identity, marriage, career, and fortune respectively.',
     'score': 9, 'categories': ['house_lord'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': [{'type':'lord_transfer','from_house':7,'to_house':7}]},
    {'text': 'Exchange of Lords (Parivartana Yoga): When the lord of one house is placed in a second house, and the lord of that second house is placed back in the first house, they exchange signs — creating a Parivartana (mutual exchange) Yoga. This powerfully connects the two houses as though both lords were in each other\'s house simultaneously. Parivartana between angular and trine lords is among the most powerful of all yogas.',
     'score': 10, 'categories': ['yoga'], 'planets': [], 'signs': [], 'houses': [],
     'formulas': [{'type':'lord_transfer','from_house':1,'to_house':10}]},
]

# ── Avastha & Vargottama helpers ─────────────────────────────────────────────
def _avastha(lon_in_sign):
    """Return the planetary maturity state (avastha) based on degree within sign."""
    d = float(lon_in_sign)
    if   d <  6: return ('Bala',    'infant — energy immature, results slow to manifest')
    elif d < 12: return ('Kumara',  'youth — developing strength, partial results')
    elif d < 18: return ('Yuva',    'adult — full strength, optimal manifestation')
    elif d < 24: return ('Vriddha', 'aging — strength declining, results waning')
    else:        return ('Mrita',   'dead — dormant energy, results severely delayed')

def _navamsha_sign(rasi_idx, lon_in_sign):
    """Calculate the Navamsha (D-9) sign index for a given rasi and degree within sign."""
    # Start rasi of navamsha sequence per sign type:
    # Movable (0,3,6,9=Aries,Cancer,Libra,Capricorn): start from Aries (0)
    # Fixed   (1,4,7,10=Taurus,Leo,Scorpio,Aquarius): start from Capricorn (9)
    # Dual    (2,5,8,11=Gemini,Virgo,Sagittarius,Pisces): start from Libra (6)
    nav_start = {0:0,1:9,2:6, 3:0,4:9,5:6, 6:0,7:9,8:6, 9:0,10:9,11:6}
    start      = nav_start.get(int(rasi_idx) % 12, 0)
    nav_idx    = int(float(lon_in_sign) / (30.0 / 9.0)) % 9
    return (start + nav_idx) % 12

def _is_vargottama(rasi_idx, lon_in_sign):
    """Return True if the planet is Vargottama (same sign in D-1 and D-9)."""
    return _navamsha_sign(rasi_idx, lon_in_sign) == (int(rasi_idx) % 12)

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
    """Return list of dicts with full planet info. House = bhava relative to Lagna."""
    raw = charts.rasi_chart(jd, place)

    # Pass 1 — locate Lagna rasi so all houses are computed relative to it
    lagna_rasi = 0
    for entry in raw:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            pid, pos = entry
            if pid == 'L':
                lagna_rasi = int(pos[0]) % 12 if isinstance(pos, (list, tuple)) and pos else 0
                break

    NAK_SPAN = 360.0 / 27.0          # degrees per nakshatra (≈13.33°)

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

        rasi_int    = int(rasi_idx) % 12
        abs_lon     = rasi_int * 30.0 + safe_float(lon_in_rasi)
        # ── Bhava (house) = rasi position relative to Lagna (1-based) ──
        house       = ((rasi_int - lagna_rasi) % 12) + 1
        sign        = RASI_NAMES[rasi_int]

        # Nakshatra & pada
        nak_idx     = int(abs_lon / NAK_SPAN) % 27
        nak_pada    = int((abs_lon % NAK_SPAN) / (NAK_SPAN / 4)) + 1

        # Planet name
        if planet_id == 'L':
            p_name, p_id, house = 'Lagna', 9, 1
        elif isinstance(planet_id, int) and planet_id < len(PLANET_NAMES):
            p_name, p_id = PLANET_NAMES[planet_id], planet_id
        else:
            try:
                p_id   = int(planet_id)
                p_name = PLANET_NAMES[p_id] if p_id < len(PLANET_NAMES) else f'P{p_id}'
            except Exception:
                p_name, p_id = str(planet_id), -1

        # Dignity
        if   EXALTATION_SIGN.get(p_name) == sign:  dignity = 'exalted'
        elif DEBILITATION_SIGN.get(p_name) == sign: dignity = 'debilitated'
        elif sign == MOOLATRIKONA.get(p_name):       dignity = 'moolatrikona'
        elif sign in OWN_SIGNS.get(p_name, []):      dignity = 'own'
        else:                                         dignity = 'neutral'

        # House type
        h_type = ('kendra'   if house in KENDRA_HOUSES  else
                  'trikona'  if house in TRIKONA_HOUSES  else
                  'dusthana' if house in DUSTHANA_HOUSES else
                  'upachaya' if house in UPACHAYA_HOUSES else 'neutral')

        lon_float    = safe_float(lon_in_rasi)
        av_name, av_desc = _avastha(lon_float)
        vargottama   = _is_vargottama(rasi_int, lon_float) if p_name not in ('Lagna',) else False
        d9_sign_idx  = _navamsha_sign(rasi_int, lon_float)
        d9_sign      = RASI_NAMES[d9_sign_idx] if p_name != 'Lagna' else sign

        positions.append({
            'id':          p_id,
            'name':        p_name,
            'rasi':        rasi_int,
            'sign':        sign,
            'house':       house,
            'house_type':  h_type,
            'lord':        SIGN_LORDS.get(sign, ''),
            'dignity':     dignity,
            'nakshatra':   NAKSHATRA_NAMES[nak_idx],
            'nak_pada':    nak_pada,
            'nak_lord':    NAKSHATRA_LORDS[nak_idx],
            'lon_in_sign': round(lon_float, 4),
            'longitude':   round(abs_lon, 4),
            'avastha':     av_name,
            'avastha_desc':av_desc,
            'vargottama':  vargottama,
            'd9_sign':     d9_sign,
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

# ── Rule extraction & formula evaluation ────────────────────────────────────

def _score_astro_relevance(text):
    tl, score = text.lower(), 0
    for kws in ASTRO_KEYWORDS.values():
        hits = sum(1 for kw in kws if kw.lower() in tl)
        if hits: score += 1 + min(hits, 4)
    return score

def _extract_formulas_from_text(text):
    """Pull structured formula tags from a sentence using FORMULA_PATTERNS."""
    formulas = []
    for pat, ftype, gnames in FORMULA_PATTERNS:
        for m in pat.finditer(text):
            formula = {'type': ftype}
            for i, gname in enumerate(gnames):
                try:
                    val = m.group(i + 1)
                except IndexError:
                    val = None
                if val:
                    if 'house' in gname:
                        try: val = int(re.sub(r'[^0-9]', '', val))
                        except: pass
                    formula[gname] = val
            # For alt-group patterns (exaltation/debilitation)
            if 'planet_alt' in formula and not formula.get('planet'):
                formula['planet'] = formula.pop('planet_alt')
            elif 'planet_alt' in formula:
                formula.pop('planet_alt')
            formulas.append(formula)
    return formulas

def _extract_rules(text, min_score=2):
    """Extract astrological rules with structured formula tags from raw text."""
    sentences = re.split(r'(?<=[.!?])\s+|\n(?=[A-Z0-9\u2018\u201c])', text)
    rules, seen = [], set()
    for sent in sentences:
        sent = sent.strip()
        if not (35 <= len(sent) <= 900): continue
        key = sent[:80].lower()
        if key in seen: continue
        seen.add(key)
        score = _score_astro_relevance(sent)
        if score < min_score: continue
        sl = sent.lower()
        cats = []
        if any(w in sl for w in ASTRO_KEYWORDS['yoga']):      cats.append('yoga')
        if any(w in sl for w in ASTRO_KEYWORDS['dasha']):     cats.append('dasha')
        if any(w in sl for w in ASTRO_KEYWORDS['house']):     cats.append('house')
        if any(w in sl for w in ASTRO_KEYWORDS['nakshatra']): cats.append('nakshatra')
        if any(w in sl for w in ASTRO_KEYWORDS['quality']):   cats.append('dignity')
        if not cats: cats.append('general')
        formulas = _extract_formulas_from_text(sent)
        houses_raw = re.findall(r'\b([1-9]|1[0-2])(?:st|nd|rd|th)?\s*(?:house|bhava)', sl)
        rules.append({
            'text':       sent,
            'score':      score,
            'categories': cats,
            'formulas':   formulas,
            'planets':    [p for p in PLANET_NAMES[:9] if p.lower() in sl],
            'signs':      [s for s in RASI_SIGNS if s.lower() in sl],
            'houses':     list({int(h) for h in houses_raw}),
        })
    rules.sort(key=lambda r: len(r['formulas']) * 3 + r['score'], reverse=True)
    return rules

def _evaluate_formula(formula, positions):
    """Return True if a structured formula applies to the current chart."""
    p_sign  = {p['name']: p['sign']  for p in positions}
    p_house = {p['name']: p['house'] for p in positions}
    lagna_r = next((p['rasi'] for p in positions if p['name'] == 'Lagna'), 0)
    ftype   = formula.get('type', '')
    try:
        if ftype == 'planet_in_sign':
            pl = formula.get('planet'); sg = formula.get('sign')
            return bool(pl and sg and p_sign.get(pl) == sg)

        if ftype == 'planet_in_house':
            pl = formula.get('planet'); h = formula.get('house')
            return bool(pl and h and p_house.get(pl) == int(h))

        if ftype == 'lord_transfer':
            fh = formula.get('from_house'); th = formula.get('to_house')
            if fh and th:
                from_sign_idx = (lagna_r + int(fh) - 1) % 12
                lord = SIGN_LORDS.get(RASI_SIGNS[from_sign_idx], '')
                return bool(lord and p_house.get(lord) == int(th))

        if ftype == 'conjunction':
            p1 = formula.get('planet1'); p2 = formula.get('planet2')
            return bool(p1 and p2 and p_house.get(p1) and p_house.get(p1) == p_house.get(p2))

        if ftype == 'exaltation':
            pl = formula.get('planet')
            return bool(pl and p_sign.get(pl) == EXALTATION_SIGN.get(pl))

        if ftype == 'debilitation':
            pl = formula.get('planet')
            return bool(pl and p_sign.get(pl) == DEBILITATION_SIGN.get(pl))

        if ftype == 'aspect':
            asp  = formula.get('aspector'); asd = formula.get('aspected')
            if asp and asd:
                ah = p_house.get(asp); bh = p_house.get(asd)
                if ah and bh:
                    diff = ((bh - ah) % 12) + 1
                    return diff == 7 or diff in SPECIAL_ASPECTS.get(asp, [])
    except Exception:
        pass
    return False

def _match_rules_to_chart(rules, positions):
    """Score rules against chart using formula-level evaluation (5×weight) + keyword fallback.
    BUILTIN_RULES are always evaluated alongside any passed-in book rules."""
    all_input = list(BUILTIN_RULES) + list(rules)  # built-ins first
    p_sign  = {p['name']: p['sign']  for p in positions}
    p_house = {p['name']: p['house'] for p in positions}
    matched = []
    seen_texts = set()
    for rule in all_input:
        txt = rule.get('text', '')
        if txt in seen_texts:
            continue
        formulas = rule.get('formulas', [])
        f_hits   = sum(1 for f in formulas if _evaluate_formula(f, positions))
        f_miss   = len(formulas) - f_hits
        # If rule has formulas but none hit, skip it
        if formulas and f_hits == 0 and f_miss > 0:
            continue
        # Keyword-level relevance fallback
        kw_rel = 0
        for pl in rule.get('planets', []):
            if pl in p_sign:
                kw_rel += 1
                if p_sign[pl] in rule.get('signs', []):  kw_rel += 3
                if p_house.get(pl) in rule.get('houses', []): kw_rel += 3
        total = f_hits * 5 + kw_rel
        if total == 0: continue
        seen_texts.add(txt)
        matched.append({
            **rule,
            'chart_relevance': total,
            'formula_hits':    f_hits,
            'formula_count':   len(formulas),
            'builtin':         rule in BUILTIN_RULES,
        })
    matched.sort(key=lambda r: r['chart_relevance'], reverse=True)
    return matched[:50]

def _house_lord_analysis(positions):
    """Build list of house lord placements for all 12 bhavas."""
    lagna_rasi = next((p['rasi'] for p in positions if p['name'] == 'Lagna'), 0)
    p_house    = {p['name']: p['house'] for p in positions}
    rows = []
    for h in range(1, 13):
        sign_idx   = (lagna_rasi + h - 1) % 12
        sign       = RASI_SIGNS[sign_idx]
        lord       = SIGN_LORDS.get(sign, '')
        lord_house = p_house.get(lord, '?')
        lord_sign  = next((p['sign'] for p in positions if p['name'] == lord), '')
        # Disposition quality
        if lord_house == '?':
            quality = 'unknown'
        elif int(lord_house) in KENDRA_HOUSES | TRIKONA_HOUSES:
            quality = 'strong'
        elif int(lord_house) in DUSTHANA_HOUSES:
            quality = 'challenged'
        else:
            quality = 'moderate'
        rows.append({
            'house':      h,
            'sign':       sign,
            'lord':       lord,
            'lord_house': lord_house,
            'lord_sign':  lord_sign,
            'signif':     HOUSE_KARKA.get(h, ''),
            'quality':    quality,
        })
    return rows

# ── Ordinal helper ──────────────────────────────────────────────────────────
def _ordinal(n):
    n = int(n)
    if n in (11, 12, 13): return f'{n}th'
    return {1:'1st', 2:'2nd', 3:'3rd'}.get(n % 10, f'{n}th')

# ── Single-planet cause+effect delineation ───────────────────────────────────
def _delineate_planet(p, positions, lagna_rasi, sb_totals=None):
    """Return a rich cause+effect paragraph for one planet placement."""
    name     = p['name']
    house    = p['house']
    sign     = p['sign']
    dignity  = p['dignity']
    nak      = p['nakshatra']
    nak_lord = p.get('nak_lord', '')
    nak_pada = p.get('nak_pada', 1)

    ruled_houses = [h for h in range(1, 13)
                    if SIGN_LORDS.get(RASI_SIGNS[(lagna_rasi + h - 1) % 12]) == name]
    karakas       = PLANET_KARAKAS.get(name, 'natural cosmic force')
    placement_sig = HOUSE_KARKA.get(house, '')

    # ── CAUSE ─────────────────────────────────────────────────────────────────
    if ruled_houses:
        ruled_sigs = [HOUSE_KARKA.get(h, f'H{h}').split(',')[0].strip() for h in ruled_houses]
        lords_txt  = ' and the '.join(
            f"{_ordinal(h)} house ({ruled_sigs[i]})" for i, h in enumerate(ruled_houses))
        cause = (f"{name} rules the {lords_txt} from your Lagna, and is currently placed "
                 f"in your {_ordinal(house)} house ({sign}, {nak} nakshatra pada {nak_pada}, "
                 f"ruled by {nak_lord})")
    else:
        cause = (f"{name} — natural significator of {karakas} — sits in your "
                 f"{_ordinal(house)} house ({sign}, {nak} nakshatra, ruled by {nak_lord})")

    # ── EFFECT ────────────────────────────────────────────────────────────────
    effects = []
    if ruled_houses:
        primary = ruled_houses[0]
        p_sig   = HOUSE_KARKA.get(primary, '').split(',')[0].strip()
        h_sig   = placement_sig.split(',')[0].strip()

        if primary == house:
            effects.append(
                f"As the lord sitting in its own bhava, {name} powerfully self-activates {p_sig}. "
                f"The native has strong natural ability and self-reliance in this domain. "
                f"Results are stable and consistent throughout life, not just during dasha periods.")
        elif house in KENDRA_HOUSES:
            effects.append(
                f"Placed in the angular {_ordinal(house)} house (kendra — {h_sig}), {name} brings "
                f"the energy of {p_sig} into material, visible, tangible expression. "
                f"Kendra placement gives maximum power to manifest in the outer world. "
                f"The connection between {p_sig} and {h_sig} is strong and productive — "
                f"these two life areas reinforce each other, and results are concrete and notable. "
                f"During {name}'s Mahadasha, the {_ordinal(primary)} house matters ({p_sig}) "
                f"manifest powerfully through the domain of the {_ordinal(house)} house.")
        elif house in TRIKONA_HOUSES:
            effects.append(
                f"Sitting in the trikona ({_ordinal(house)} house — {h_sig}), {name} brings "
                f"dharmic grace and past-life merit to {p_sig}. "
                f"Trikona placements indicate the Universe supports these areas — the native finds "
                f"that {p_sig} flows with relative ease. Spiritual blessings reinforce worldly "
                f"progress, and this planet delivers results with less friction than other placements.")
        elif house in DUSTHANA_HOUSES:
            effects.append(
                f"Placed in the {_ordinal(house)} house (dusthana — {h_sig}), {name} creates "
                f"initial turbulence, delays, and hidden challenges around {p_sig}. "
                f"The native may face recurring obstacles or losses in this area before mastery. "
                f"Check for Viparita Raja Yoga: if the lord of this same dusthana is also in a "
                f"dusthana, unexpected gains emerge from apparent setbacks. "
                f"With sustained effort and remediation for {name}, this placement ultimately "
                f"builds exceptional resilience and unconventional success.")
        else:
            effects.append(
                f"In the neutral {_ordinal(house)} house ({h_sig}), {name} links the energy of "
                f"{p_sig} with {h_sig}, creating a karmic connection where progress in one area "
                f"influences the other. Results here are moderate but consistent.")

    # ── DIGNITY ──────────────────────────────────────────────────────────────
    if dignity == 'exalted':
        effects.append(
            f"{name} is exalted in {sign} — at its absolute maximum strength. "
            f"The native receives peak, exceptional results from every area {name} signifies. "
            f"Natural significations ({karakas.split(',')[0]}) flourish especially during "
            f"{name} Mahadasha. An exalted planet is the most powerful positive force in the chart.")
    elif dignity == 'debilitated':
        nb_lord    = SIGN_LORDS.get(sign, '')
        exalt_sg   = EXALTATION_SIGN.get(name, '')
        exalt_lord = SIGN_LORDS.get(exalt_sg, '') if exalt_sg else ''
        effects.append(
            f"{name} is debilitated (neecha) in {sign} — it struggles to deliver its best results, "
            f"and the life areas it governs may feel chronically difficult or blocked. "
            f"Check for Neecha Bhanga: if {nb_lord} (sign lord) or "
            f"{exalt_lord} (exaltation lord) sits in a kendra or trikona, "
            f"the debilitation is cancelled and becomes a powerful Raja Yoga — "
            f"exceptional results after initial struggle.")
    elif dignity == 'own':
        effects.append(
            f"In its own sign {sign}, {name} is at home — it delivers steady, reliable, "
            f"and consistent results throughout life. Own-sign planets are dependable pillars.")
    elif dignity == 'moolatrikona':
        effects.append(
            f"In moolatrikona sign {sign}, {name} is especially purposeful and generous — "
            f"it expresses its best qualities outward, bringing benefits to the native and those "
            f"around them. This is stronger than own-sign for giving results to others.")

    # ── SHAD BALA ────────────────────────────────────────────────────────────
    if sb_totals and name in sb_totals:
        val = sb_totals[name]
        if val >= 150:
            effects.append(
                f"Shad Bala confirms superior strength ({val:.0f} Rupas ≥ 150) — "
                f"this planet's dasha periods will be especially potent and life-defining.")
        elif val < 80:
            effects.append(
                f"Shad Bala shows below-threshold strength ({val:.0f} Rupas). "
                f"Gemstone, mantra japa, and charity for {name} will help unlock its potential.")

    # ── ASPECTS ──────────────────────────────────────────────────────────────
    asp7 = ((house - 1 + 6) % 12) + 1
    asp_houses = [asp7] + [((house - 1 + s - 1) % 12) + 1 for s in SPECIAL_ASPECTS.get(name, [])]
    aspected_pls = [q['name'] for q in positions
                    if q['name'] not in ('Lagna', name) and q['house'] in asp_houses]
    if aspected_pls:
        effects.append(
            f"{name} casts its aspect on the {_ordinal(asp7)} house"
            + (f", directly influencing {', '.join(aspected_pls)}" if aspected_pls else '')
            + f" — adding its nature to those planetary expressions.")

    return cause + '. ' + ' '.join(effects)


# ── Discussion response generator ────────────────────────────────────────────
def _generate_discussion_response(message, positions, all_rules, raja_yogas=None, doshas=None):
    """Return (response_text, relevant_planets, matched_rules) for a life discussion query."""
    msg_lower = message.lower()
    lagna = next((p for p in positions if p['name'] == 'Lagna'), None)
    if not lagna:
        return "Please enter your birth details to begin the discussion.", [], []

    lagna_rasi = lagna['rasi']
    lagna_sign = lagna['sign']

    detected_areas = [area for area, kws in LIFE_AREA_KEYWORDS.items()
                      if any(kw in msg_lower for kw in kws)]
    if not detected_areas:
        detected_areas = ['career', 'wealth', 'marriage', 'health']

    relevant_houses = set()
    for area in detected_areas:
        relevant_houses.update(LIFE_AREA_HOUSES.get(area, []))

    seen, unique_planets = set(), []
    for p in positions:
        if p['name'] == 'Lagna': continue
        is_rel = p['house'] in relevant_houses
        if not is_rel:
            for h in relevant_houses:
                if SIGN_LORDS.get(RASI_SIGNS[(lagna_rasi + h - 1) % 12]) == p['name']:
                    is_rel = True; break
        if is_rel and p['name'] not in seen:
            seen.add(p['name']); unique_planets.append(p)

    area_blocks = []
    for area in detected_areas[:4]:
        houses = LIFE_AREA_HOUSES.get(area, [])
        if not houses: continue
        ph        = houses[0]
        h_sign    = RASI_SIGNS[(lagna_rasi + ph - 1) % 12]
        lord_name = SIGN_LORDS.get(h_sign, '')
        lord_p    = next((p for p in positions if p['name'] == lord_name), None)
        occupants = [p for p in positions if p['name'] != 'Lagna' and p['house'] == ph]
        sig       = HOUSE_KARKA.get(ph, area)

        lines = [f"### {area.title()} → {_ordinal(ph)} House ({h_sign})"]
        lines.append(f"The {_ordinal(ph)} house governs: *{sig}*.")

        if lord_p:
            lh     = lord_p['house']
            lh_sig = HOUSE_KARKA.get(lh, '').split(',')[0].strip()
            if lh in KENDRA_HOUSES or lh in TRIKONA_HOUSES:
                strength = f"strongly placed in a {'kendra' if lh in KENDRA_HOUSES else 'trikona'} ({_ordinal(lh)} house — {lh_sig})"
                effect   = (f"This gives natural strength and positive flow to your {area}. "
                            f"Kendra/trikona placement means the Universe actively supports this area. "
                            f"During {lord_name}'s Mahadasha, major {area} milestones occur with less friction.")
            elif lh in DUSTHANA_HOUSES:
                strength = f"placed in a dusthana ({_ordinal(lh)} house — {lh_sig})"
                effect   = (f"This creates initial obstacles, hidden challenges, and delays in {area}. "
                            f"Check for Viparita Raja Yoga (lord of dusthana in dusthana = unexpected gains). "
                            f"Targeted remediation for {lord_name} will specifically improve {area} outcomes.")
            else:
                strength = f"moderately placed ({_ordinal(lh)} house — {lh_sig})"
                effect   = (f"This gives steady, moderate {area} results. "
                            f"Consistent effort over time yields meaningful progress in this domain.")

            dign_note = ''
            if lord_p['dignity'] == 'exalted':
                dign_note = f" **Bonus**: {lord_name} is exalted — peak results in {area}."
            elif lord_p['dignity'] == 'debilitated':
                dign_note = (f" **Note**: {lord_name} is debilitated — check for Neecha Bhanga "
                             f"which can transform this into exceptional {area} results.")

            lines.append(f"**Cause**: Your {area} lord {lord_name} is {strength} in {lord_p['sign']}.")
            lines.append(f"**Effect**: {effect}{dign_note}")

        if occupants:
            occ_parts = [f"{p['name']} ({PLANET_KARAKAS.get(p['name'],'').split(',')[0]})" for p in occupants]
            lines.append(
                f"**Direct occupants**: {', '.join(occ_parts)} sit in your {_ordinal(ph)} house, "
                f"adding their natures directly to {area} — making this a multidimensional life area.")

        area_blocks.append('\n'.join(lines))

    matched   = _match_rules_to_chart(all_rules, positions)
    area_kws  = [kw for a in detected_areas for kw in LIFE_AREA_KEYWORDS.get(a, [])]
    area_rules = []
    for rule in matched:
        if any(kw in rule['text'].lower() for kw in area_kws):
            area_rules.append(rule)
        if len(area_rules) >= 6: break

    parts = [f"Reading your **{lagna_sign} Lagna** chart for: **{', '.join(a.title() for a in detected_areas)}**\n"]
    parts.extend(area_blocks)

    if area_rules:
        parts.append("\n---\n### Classical Texts on Your Query")
        for rule in area_rules[:3]:
            fh = rule.get('formula_hits', 0); fc = rule.get('formula_count', 0)
            badge = f" ✓ *verified {fh}/{fc} formulas*" if fh > 0 else ""
            parts.append(f"> \"{rule['text'][:240]}{'...' if len(rule['text']) > 240 else ''}\"  {badge}")

    if raja_yogas and any(a in detected_areas for a in ['career','wealth','marriage','relationship']):
        parts.append("\n---\n### Relevant Yogas in Your Chart")
        for ry in raja_yogas[:2]:
            effect_txt = re.sub(r'<[^>]+>', ' ', str(ry.get('effect', ''))).strip()[:200]
            if effect_txt:
                parts.append(f"- **{ry.get('name', 'Yoga')}**: {effect_txt}")

    if doshas:
        active = {k: v for k, v in doshas.items()
                  if 'no' not in str(v).lower() and 'not' not in str(v).lower()}
        if active and any(a in detected_areas for a in ['marriage','health','longevity']):
            parts.append("\n---\n### Active Doshas Relevant to Your Query")
            for dname in list(active.keys())[:2]:
                parts.append(f"- **{dname}** is active — consult a Jyotishi for personalised remediation.")

    return '\n\n'.join(parts), unique_planets, area_rules


# ── Chart narrative interpretation ───────────────────────────────────────────
def _deep_interpret(positions, raja_yogas, doshas, shad_bala, matched_rules=None):
    """Generate planet-by-planet cause+effect delineation of the natal chart."""
    from collections import defaultdict
    paras      = []
    lagna      = next((p for p in positions if p['name'] == 'Lagna'), None)
    if not lagna:
        return [{'title':'Error','text':'Lagna not found.','category':'error','icon':'⚠'}]

    lagna_rasi = lagna['rasi']
    lagna_sign = lagna['sign']
    sb_totals  = shad_bala.get('totals', {}) if isinstance(shad_bala, dict) else {}

    SIGN_DESC = {
        'Aries':       'energetic, pioneering and self-driven — Mars-ruled fire, the natural doer',
        'Taurus':      'patient, steadfast and materially grounded — Venus-ruled earth, the natural builder',
        'Gemini':      'communicative, versatile and intellectually curious — Mercury-ruled air, the natural thinker',
        'Cancer':      'nurturing, emotionally sensitive and home-oriented — Moon-ruled water, the natural caretaker',
        'Leo':         'regal, creative and leadership-focused — Sun-ruled fire, the natural king',
        'Virgo':       'analytical, service-oriented and detail-conscious — Mercury-ruled earth, the natural perfectionist',
        'Libra':       'harmonious, relationship-focused and justice-seeking — Venus-ruled air, the natural diplomat',
        'Scorpio':     'intense, transformative and depth-seeking — Mars-ruled water, the natural investigator',
        'Sagittarius': 'philosophical, expansive and truth-seeking — Jupiter-ruled fire, the natural seeker',
        'Capricorn':   'disciplined, achievement-oriented and structured — Saturn-ruled earth, the natural achiever',
        'Aquarius':    'innovative, humanitarian and unconventional — Saturn-ruled air, the natural visionary',
        'Pisces':      'compassionate, mystical and spiritually attuned — Jupiter-ruled water, the natural dreamer',
    }

    # ── 1. LAGNA — the foundation of life ────────────────────────────────────
    ll_name    = SIGN_LORDS.get(lagna_sign, '')
    ll         = next((p for p in positions if p['name'] == ll_name), None)
    lagna_text = (
        f"Your Ascendant (Lagna) is in {lagna_sign} at {lagna['lon_in_sign']:.2f}°, "
        f"in {lagna['nakshatra']} nakshatra (pada {lagna['nak_pada']}, "
        f"lord: {lagna['nak_lord']}). This makes you fundamentally "
        f"{SIGN_DESC.get(lagna_sign, '')}. "
    )
    if ll:
        lh_sig = HOUSE_KARKA.get(ll['house'], '')
        if ll['house'] in KENDRA_HOUSES | TRIKONA_HOUSES:
            ll_strength = f"powerfully placed in the {_ordinal(ll['house'])} house (kendra/trikona)"
            ll_effect   = (
                f"This is an excellent configuration — your Lagna lord is strong, indicating "
                f"good vitality, a clear sense of self, and the ability to manifest your Ascendant's "
                f"nature in the world. The {_ordinal(ll['house'])} house domains "
                f"({lh_sig.split(',')[0]}) become a central life theme through which you express "
                f"your core identity. Expect strong results during {ll_name}'s Mahadasha.")
        elif ll['house'] in DUSTHANA_HOUSES:
            ll_strength = f"placed in a dusthana ({_ordinal(ll['house'])} house)"
            ll_effect   = (
                f"The Lagna lord in a dusthana creates some life challenges — the native may "
                f"encounter obstacles in health, self-expression, or life direction, particularly "
                f"early in life. However, this placement also builds extraordinary resilience. "
                f"Check for Viparita Raja Yoga if the dusthana lord itself is in a dusthana.")
        else:
            ll_strength = f"moderately placed in the {_ordinal(ll['house'])} house"
            ll_effect   = (
                f"Your life force flows through the {_ordinal(ll['house'])} house domain "
                f"({lh_sig.split(',')[0]}) — these matters shape your purpose and fulfillment.")
        lagna_text += (
            f"Your Lagna lord {ll_name} ({PLANET_KARAKAS.get(ll_name,'').split(',')[0]}) "
            f"is {ll_strength} in {ll['sign']}. {ll_effect}"
        )
    paras.append({
        'title':    f"{lagna_sign} Ascendant — Your Core Life Blueprint",
        'text':     lagna_text,
        'category': 'lagna',
        'icon':     '↑',
    })

    # ── 2. PLANET-BY-PLANET cause+effect delineation ─────────────────────────
    for pname in ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']:
        p = next((x for x in positions if x['name'] == pname), None)
        if not p: continue
        text      = _delineate_planet(p, positions, lagna_rasi, sb_totals)
        h_type_lbl= {
            'kendra':   'Kendra — Angular',
            'trikona':  'Trikona — Trine',
            'dusthana': 'Dusthana — Challenging',
            'upachaya': 'Upachaya — Growth',
            'neutral':  'Neutral',
        }.get(p['house_type'], p['house_type'].title())
        d_icon = {'exalted':'⬆','debilitated':'⬇','moolatrikona':'★','own':'◆','neutral':'·'}.get(p['dignity'],'·')
        # Append Avastha and Vargottama data to the planet text
        av_tag = p.get('avastha','')
        vargo  = p.get('vargottama', False)
        d9_s   = p.get('d9_sign', '')
        av_colors = {'Bala':'⚪','Kumara':'🟡','Yuva':'🟢','Vriddha':'🟠','Mrita':'🔴'}
        av_note = f" | Avastha: {av_colors.get(av_tag,'')}{av_tag} ({p.get('avastha_desc','')})"
        vargo_note = f" | ✨ VARGOTTAMA (D-9 also {d9_s} — doubly strong, exceptional stability)" if vargo else f" | D-9: {d9_s}"
        paras.append({
            'title':    f"{pname} in {p['sign']} · H{p['house']} ({h_type_lbl}) {d_icon}",
            'text':     text + av_note + vargo_note,
            'category': 'planet',
            'icon':     d_icon,
            'meta': {
                'planet':     pname,
                'house':      p['house'],
                'sign':       p['sign'],
                'dignity':    p['dignity'],
                'house_type': p['house_type'],
                'nakshatra':  p['nakshatra'],
                'avastha':    av_tag,
                'vargottama': vargo,
                'd9_sign':    d9_s,
            },
        })

    # ── 3. CONJUNCTIONS — multi-planet house analysis ────────────────────────
    house_occ = defaultdict(list)
    for p in positions:
        if p['name'] != 'Lagna': house_occ[p['house']].append(p)
    for h, occ in sorted(house_occ.items()):
        if len(occ) < 2: continue
        names    = [p['name'] for p in occ]
        h_sig    = HOUSE_KARKA.get(h, '')
        malefics = {'Sun','Mars','Saturn','Rahu','Ketu'}
        mal_cnt  = sum(1 for n in names if n in malefics)
        ben_cnt  = len(names) - mal_cnt
        k_parts  = [PLANET_KARAKAS.get(n,'').split(',')[0].strip() for n in names]
        if mal_cnt > ben_cnt:
            mix_txt = (f"Malefics dominate ({', '.join(n for n in names if n in malefics)}), "
                       f"intensifying challenges in {h_sig.split(',')[0]} but also creating "
                       f"fierce focus, resilience, and the potential for exceptional achievement through struggle. ")
        elif ben_cnt > mal_cnt:
            mix_txt = (f"Benefics dominate, creating natural ease and abundance in "
                       f"{h_sig.split(',')[0]}. ")
        else:
            mix_txt = f"A mixed conjunction creates complex, layered results in {h_sig.split(',')[0]}. "
        conj_text = (
            f"{' + '.join(names)} all converge in your {_ordinal(h)} house "
            f"({occ[0]['sign'] if occ else ''} — {h_sig}). {mix_txt}"
            f"Combined natures: {'; '.join(f'{n} ({k})' for n,k in zip(names,k_parts))}. "
            f"The {_ordinal(h)} house becomes a zone of intense, layered energy. "
            f"During any of these planets' Mahadasha, the matters of this house are powerfully "
            f"activated and demand the native's full attention and engagement."
        )
        paras.append({
            'title':    f"Conjunction: {' + '.join(names)} in {_ordinal(h)} House ({h_sig.split(',')[0]})",
            'text':     conj_text,
            'category': 'conjunction',
            'icon':     '⚯',
        })

    # ── 4. YOGA-KARAKA — the most powerful planet ─────────────────────────────
    kl, tl = set(), set()
    for h in range(1, 13):
        lord = SIGN_LORDS.get(RASI_SIGNS[(lagna_rasi + h - 1) % 12], '')
        if h in KENDRA_HOUSES:  kl.add(lord)
        if h in TRIKONA_HOUSES: tl.add(lord)
    for yk in sorted(kl & tl - {''}):
        yk_p = next((p for p in positions if p['name'] == yk), None)
        if not yk_p: continue
        yk_h_sig = HOUSE_KARKA.get(yk_p['house'], '').split(',')[0]
        placement_quality = ('amplified by angular strength' if yk_p['house'] in KENDRA_HOUSES
                             else 'blessed by trine placement' if yk_p['house'] in TRIKONA_HOUSES
                             else 'in a challenging position — remediation recommended')
        paras.append({
            'title':    f"Yoga-Karaka: {yk} — Most Powerful Planet in Your Chart",
            'text':     (
                f"{yk} rules both a kendra and a trikona from your {lagna_sign} Lagna — "
                f"making it your single most powerful planet, the Yoga-Karaka. "
                f"When well-placed, it creates Raja Yoga single-handedly. "
                f"Currently in your {_ordinal(yk_p['house'])} house ({yk_p['sign']} — {yk_h_sig}), "
                f"its power is {placement_quality}. "
                f"The Mahadasha of {yk} is the most pivotal period of your life — it determines "
                f"peak career, status, wealth, and dharmic fulfillment. "
                f"Strengthen {yk} through its specific gemstone, mantra, and charitable acts "
                f"and never deliberately weaken it."
            ),
            'category': 'yoga',
            'icon':     '👑',
        })

    # ── 5. RAJA YOGAS with cause and effect ──────────────────────────────────
    if raja_yogas:
        for ry in raja_yogas[:4]:
            name_txt   = ry.get('name', ry.get('type', 'Raja Yoga'))
            desc       = str(ry.get('description', ''))[:300]
            effect_raw = re.sub(r'<[^>]+>', ' ', str(ry.get('effect', ''))).strip()[:400]
            paras.append({
                'title':    f"Raja Yoga: {name_txt}",
                'text':     (
                    f"**Cause**: {desc if desc else name_txt + ' is present in this chart.'} "
                    f"**Effect**: {effect_raw if effect_raw else 'This yoga confers elevated status, recognition, and prosperity — especially during the dasha periods of the planets forming this combination.'}"
                ),
                'category': 'yoga',
                'icon':     '♛',
            })

    # ── 6. DOSHAS — cause, effect and remedy ─────────────────────────────────
    DOSHA_REMEDIES = {
        'Manglik Dosha':       'Kumbh Vivah ritual, coral gemstone, Tuesday fasting, Hanuman Chalisa.',
        'Kala Sarpa Dosha':    'Rahu-Ketu puja, Nagpanchami worship, Trimbakeshwar temple ritual.',
        'Guru Chandala Dosha': 'Jupiter mantra (Om Brihaspataye Namaha), yellow sapphire, Thursday fasting.',
        'Pitru Dosha':         'Pitru Tarpan on Amavasya, feeding crows and Brahmins, charity on Saturdays.',
        'Shrapit Dosha':       'Saturn mantra, blue sapphire, Shani Shanti puja, oil donation.',
        'Ganda Moola Dosha':   'Nakshatra Shanti puja, specific deity worship for birth nakshatra.',
        'Ghata Dosha':         'Ghata Shanti puja, fasting on the relevant weekday.',
    }
    active_doshas = {k: v for k, v in doshas.items()
                     if 'no' not in str(v).lower() and 'not' not in str(v).lower()}
    for dname, dtext in list(active_doshas.items())[:3]:
        remedy   = DOSHA_REMEDIES.get(dname, 'Consult a qualified Jyotishi for personalised remediation.')
        d_body   = str(dtext)
        d_excerpt= d_body[:300] if len(d_body) > 50 else f'{dname} is active in this chart.'
        paras.append({
            'title':    f"Dosha: {dname}",
            'text':     (
                f"**What it is**: {d_excerpt} "
                f"**Effect**: This karmic pattern influences the life areas ruled by the involved "
                f"planets — challenges and imbalances are most pronounced during those planets' "
                f"Mahadasha and Antardasha periods. "
                f"**Remedy**: {remedy}"
            ),
            'category': 'dosha',
            'icon':     '⚠',
        })

    # ── 7. KEY HOUSE LORD CHAINS ─────────────────────────────────────────────
    for row in _house_lord_analysis(positions):
        if row['house'] not in {1, 2, 4, 5, 7, 9, 10, 11}: continue
        if row['quality'] not in ('strong', 'challenged'): continue
        sig = row['signif'].split(',')[0].strip()
        lh  = int(row['lord_house']) if str(row['lord_house']).isdigit() else 0
        if lh == 0: continue
        if row['quality'] == 'strong':
            pt = 'kendra' if lh in KENDRA_HOUSES else 'trikona'
            effect_txt = (
                f"The {_ordinal(row['house'])} house lord ({row['lord']}) sits in a "
                f"{pt} ({_ordinal(lh)} house) — a positive, empowered placement. "
                f"The life areas of {sig} are naturally supported and the native tends to "
                f"succeed here. During {row['lord']}'s Mahadasha, significant positive "
                f"milestones in {sig} are expected with relatively less friction.")
        else:
            effect_txt = (
                f"The {_ordinal(row['house'])} house lord ({row['lord']}) sits in a dusthana "
                f"({_ordinal(lh)} house) — creating obstacles, recurring challenges, and "
                f"potential setbacks in {sig}. The native faces karmic tests in this domain. "
                f"With targeted remediation for {row['lord']} and sustained effort, these "
                f"obstacles can be overcome — often building greater strength than easy placements.")
        paras.append({
            'title':    f"H{row['house']} ({sig}) — Lord {row['lord']} in H{lh}: {row['quality'].title()}",
            'text':     effect_txt,
            'category': 'house_lord',
            'icon':     '✓' if row['quality'] == 'strong' else '⚑',
        })

    # ── 8. CLASSICAL TEXT MATCHES ────────────────────────────────────────────
    if matched_rules:
        formula_matched = [r for r in matched_rules if r.get('formula_hits', 0) > 0]
        for rule in formula_matched[:6]:
            cats = rule.get('categories', ['general'])
            src  = 'Built-in Classical Rule' if rule.get('builtin') else 'Uploaded Book Rule'
            paras.append({
                'title':    f"📖 {src} ({cats[0].title()}): Verified Against Your Chart",
                'text':     (
                    f"\"{rule['text']}\" "
                    f"[Formula-verified: {rule['formula_hits']}/{rule['formula_count']} formulas "
                    f"match this chart — Relevance score: {rule['chart_relevance']}]"
                ),
                'category': 'classical',
                'icon':     '📖',
            })
        if len(matched_rules) > 6:
            paras.append({
                'title':    f"📚 {len(matched_rules)} Total Classical Rules Matched",
                'text':     (
                    f"{len(formula_matched)} are formula-verified against your actual planetary positions. "
                    f"Sources include built-in Parashari rules, V.P. Goel's Divisional Charts, "
                    f"Krishna Kumar's Secret of Vargas, M.N. Kedar's Delineation methodology, "
                    f"and N.N. Sharma's Divisional Chart research (K.N. Rao school). "
                    f"Browse all matched rules in the Rule Library for complete classical backing."
                ),
                'category': 'classical',
                'icon':     '📚',
            })

    # ── 9. VARGOTTAMA & AVASTHA — Microscopic Planetary Strength Analysis ────
    vargo_planets = [p for p in positions if p.get('vargottama') and p['name'] != 'Lagna']
    if vargo_planets:
        vargo_texts = []
        for p in vargo_planets:
            ruled = [h for h in range(1,13)
                     if SIGN_LORDS.get(RASI_SIGNS[(lagna_rasi+h-1)%12]) == p['name']]
            ruled_sigs = [HOUSE_KARKA.get(h,'').split(',')[0] for h in ruled]
            sigs_txt = ' and '.join(ruled_sigs) if ruled_sigs else PLANET_KARAKAS.get(p['name'],'').split(',')[0]
            vargo_texts.append(
                f"**{p['name']} is Vargottama** — in {p['sign']} in both your birth chart and Navamsha (D-9). "
                f"This is the rarest strength-multiplier in Jyotish: the planet's energy is anchored, "
                f"doubled, and exceptionally stable. {p['name']}'s significations — {sigs_txt} — "
                f"deliver their results with unusual consistency and depth across all life periods, not just during the Mahadasha."
            )
        paras.append({
            'title':    f"✨ Vargottama Planets: {', '.join(p['name'] for p in vargo_planets)} — Doubly Anchored Strength",
            'text':     ' | '.join(vargo_texts),
            'category': 'dignity',
            'icon':     '✨',
        })

    # ── 10. AVASTHA MATRIX — Planetary Maturity States (Kedar) ──────────────
    real_planets = [p for p in positions if p['name'] not in ('Lagna',) and p['name'] in
                    ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']]
    av_groups = {'Yuva':[], 'Kumara':[], 'Vriddha':[], 'Bala':[], 'Mrita':[]}
    for p in real_planets:
        av = p.get('avastha','Yuva')
        if av in av_groups: av_groups[av].append(p['name'])
    av_text_parts = []
    av_icons = {'Yuva':'🟢','Kumara':'🟡','Bala':'⚪','Vriddha':'🟠','Mrita':'🔴'}
    av_intros = {
        'Yuva':    'at full maturity, delivering peak, optimal results right now',
        'Kumara':  'in developing youth, delivering partial results with growing strength',
        'Bala':    'in infant state, immature — results will come slowly; patience required',
        'Vriddha': 'in aging state, results declining — past-life gifts fading, effort needed',
        'Mrita':   'in dormant state — severely restricted; gemstone/mantra remediation advised',
    }
    for av_state in ['Yuva','Kumara','Vriddha','Bala','Mrita']:
        pls = av_groups[av_state]
        if pls:
            av_text_parts.append(f"{av_icons[av_state]} **{av_state}** ({av_intros[av_state]}): {', '.join(pls)}")
    paras.append({
        'title':    'Avastha Matrix — Planetary Maturity States (Kedar Methodology)',
        'text':     (
            'Based on each planet\'s degree within its sign, their current strength-state (avastha) is: '
            + ' | '.join(av_text_parts)
            + '. Note: Avastha applies to the dasha results — even a well-placed planet in Mrita avastha delivers muted results during its Mahadasha unless remediated.'
        ),
        'category': 'dignity',
        'icon':     '⚖',
    })

    # ── 11. NAKSHATRA-LORD INHERITANCE CHAIN ─────────────────────────────────
    nak_chain_parts = []
    for p in real_planets:
        nak_lord = p.get('nak_lord', '')
        if not nak_lord or nak_lord == p['name']: continue
        nak_lord_p = next((x for x in positions if x['name'] == nak_lord), None)
        nak_lord_house = nak_lord_p['house'] if nak_lord_p else '?'
        nak_lord_sign  = nak_lord_p['sign']  if nak_lord_p else '?'
        nak_lord_dig   = nak_lord_p.get('dignity','neutral') if nak_lord_p else 'neutral'
        dig_note = {'exalted':' (exalted — strongly positive)',' debilitated':' (debilitated — weakened)'}.get(nak_lord_dig,'')
        karaka_chain = PLANET_KARAKAS.get(nak_lord,'').split(',')[0]
        nak_chain_parts.append(
            f"**{p['name']}** in {p['nakshatra']} (lord: {nak_lord}) — "
            f"{p['name']} inherits {nak_lord}'s qualities ({karaka_chain}). "
            f"{nak_lord} sits in H{nak_lord_house} ({nak_lord_sign}{dig_note}), "
            f"so {p['name']}'s expression is filtered through {nak_lord}'s house-{nak_lord_house} agenda"
        )
    if nak_chain_parts:
        paras.append({
            'title':    'Nakshatra-Lord Inheritance Chain (M.N. Kedar Methodology)',
            'text':     (
                'Each planet in your chart operates through the filter of its nakshatra lord '
                '(the ruler of the star-division it occupies). This "inheritance" shapes HOW the planet '
                'expresses itself — far beyond mere sign placement: '
                + '; '.join(nak_chain_parts[:6])
            ),
            'category': 'nakshatra',
            'icon':     '🌟',
        })

    # ── 12. DIVISIONAL CHART GUIDANCE (V.P. Goel + Krishna Kumar) ───────────
    paras.append({
        'title':    'Divisional Chart Reading Map (V.P. Goel + Krishna Kumar)',
        'text':     (
            'To complete this analysis with surgical precision, cross-reference these divisional charts: '
            '**D-9 (Navamsha)**: Confirm marriage quality — examine 7th lord and Venus in D-9; '
            'any Vargottama planet is anchored here and delivers exceptional results. '
            '**D-10 (Dashamsha)**: Career domain and peak — check Sun, 10th lord, and their dignity in D-10. '
            '**D-7 (Saptamsha)**: Children\'s quality and timing — Jupiter\'s condition in D-7 is paramount. '
            '**D-12 (Dwadashamsha)**: Parental blessings — Sun (9th lord in D-12) for father; Moon (4th lord in D-12) for mother. '
            '**D-4 (Chaturthamsha)**: Property and domestic fortune — 4th lord\'s D-4 position confirms or denies real estate gains. '
            '**D-20 (Vimshamsha)**: Spiritual progress — Ketu and 9th/12th lords in D-20 for liberation potential. '
            'Per K.N. Rao\'s three-point rule: confirm every major prediction with 3 houses + 3 planets + 2 divisional charts before stating it as certain.'
        ),
        'category': 'classical',
        'icon':     '📊',
    })

    # ── 13. PAC SYNTHESIS — Most Powerfully Connected Planets ───────────────
    p_house_map = {p['name']: p['house'] for p in positions if p['name'] != 'Lagna'}
    pac_scores = {}
    for p in real_planets:
        score = 0
        # Position connections (planets sharing the same house)
        conjuncts = [q for q in real_planets if q['name'] != p['name'] and q['house'] == p['house']]
        score += len(conjuncts) * 2
        # Aspect connections
        asp7 = ((p['house'] - 1 + 6) % 12) + 1
        asp_other = [((p['house'] - 1 + s - 1) % 12) + 1 for s in SPECIAL_ASPECTS.get(p['name'], [])]
        asp_planets = [q for q in real_planets
                       if q['name'] != p['name'] and q['house'] in ([asp7] + asp_other)]
        score += len(asp_planets)
        # Rulership connections (ruling key houses)
        ruled = [h for h in range(1,13)
                 if SIGN_LORDS.get(RASI_SIGNS[(lagna_rasi+h-1)%12]) == p['name']]
        score += len([h for h in ruled if h in KENDRA_HOUSES | TRIKONA_HOUSES]) * 3
        pac_scores[p['name']] = score
    top_pac = sorted(pac_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    if top_pac:
        pac_desc = []
        for pname, sc in top_pac:
            p = next((x for x in positions if x['name'] == pname), None)
            if p:
                pac_desc.append(
                    f"**{pname}** (PAC score {sc}) in H{p['house']} ({p['sign']}) — "
                    f"the most multidimensionally connected planet, making it a dominant life-shaper"
                )
        paras.append({
            'title':    'PAC Analysis — Most Powerfully Connected Planets (Kedar Methodology)',
            'text':     (
                'PAC (Position, Aspect, Conjunction) analysis identifies which planets have the most '
                'connections across your chart — these are the true engines of your fate: '
                + '; '.join(pac_desc)
                + '. These planets\' Mahadasha periods are the most transformative and important periods '
                'of your life. Strengthen them proactively.'
            ),
            'category': 'yoga',
            'icon':     '🔗',
        })

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

# ── API: Life Discussion ─────────────────────────────────────────────────────
@app.route('/api/discuss', methods=['POST'])
def api_discuss():
    try:
        data     = request.get_json(force=True)
        message  = data.get('message', '').strip()
        chart_id = data.get('chart_id')
        book_ids = data.get('book_ids', [])

        if not message:
            return jsonify({'error': 'message is required'}), 400

        # Resolve chart positions
        if chart_id and chart_id in _chart_cache:
            cached     = _chart_cache[chart_id]
            positions  = cached['planets']
            raja_yogas = cached.get('raja_yogas', [])
            doshas     = cached.get('doshas', {})
        elif 'year' in data or 'date' in data:
            place, jd, lat, lon, tz = parse_birth_data(data)
            positions  = get_planet_positions(jd, place)
            raja_yogas = []
            doshas     = {}
        else:
            return jsonify({'error': 'chart_id or birth data required'}), 400

        # Aggregate rules from all books (or specified books)
        all_rules = []
        books_to_use = book_ids if book_ids else list(_book_store.keys())
        for bid in books_to_use:
            if bid in _book_store:
                all_rules.extend(_book_store[bid].get('rules', []))

        response_text, relevant_planets, matched_rules = _generate_discussion_response(
            message, positions, all_rules,
            raja_yogas=raja_yogas, doshas=doshas
        )

        return jsonify({
            'response':         response_text,
            'relevant_planets': relevant_planets,
            'matched_rules':    matched_rules,
            'book_count':       len(books_to_use),
            'rule_count':       len(all_rules),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── API: Rule Library ─────────────────────────────────────────────────────────
@app.route('/api/rule-library', methods=['GET'])
def api_rule_library():
    """Aggregate and filter rules across all uploaded books."""
    try:
        planet_filter   = request.args.get('planet', '').strip()
        sign_filter     = request.args.get('sign', '').strip()
        house_filter    = request.args.get('house', '').strip()
        ftype_filter    = request.args.get('formula_type', '').strip()
        q_filter        = request.args.get('q', '').strip().lower()
        book_filter     = request.args.get('book_id', '').strip()
        min_score       = int(request.args.get('min_score', 2))
        limit           = min(int(request.args.get('limit', 200)), 1000)

        aggregate = []
        books_to_search = [book_filter] if book_filter and book_filter in _book_store else list(_book_store.keys())

        for bid in books_to_search:
            store = _book_store.get(bid, {})
            for rule in store.get('rules', []):
                if rule.get('score', 0) < min_score: continue
                if planet_filter and planet_filter not in rule.get('planets', []): continue
                if sign_filter   and sign_filter   not in rule.get('signs', []):   continue
                if house_filter  and int(house_filter) not in rule.get('houses', []): continue
                if ftype_filter  and not any(f.get('type') == ftype_filter for f in rule.get('formulas', [])): continue
                if q_filter      and q_filter not in rule.get('text', '').lower(): continue
                aggregate.append({**rule, 'book_id': bid, 'book_name': store.get('filename', bid)})

        aggregate.sort(key=lambda r: len(r.get('formulas',[])) * 3 + r.get('score', 0), reverse=True)

        return jsonify({
            'total':    len(aggregate),
            'rules':    aggregate[:limit],
            'books':    len(books_to_search),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rule-library/search', methods=['POST'])
def api_rule_library_search():
    """Match aggregated rules from multiple books against a chart."""
    try:
        data     = request.get_json(force=True)
        book_ids = data.get('book_ids', list(_book_store.keys()))
        if not book_ids:
            book_ids = list(_book_store.keys())

        # Build chart positions
        chart_id = data.get('chart_id')
        if chart_id and chart_id in _chart_cache:
            positions = _chart_cache[chart_id]['planets']
        else:
            place, jd, lat, lon, tz = parse_birth_data(data)
            positions = get_planet_positions(jd, place)

        # Aggregate rules
        all_rules = []
        for bid in book_ids:
            if bid in _book_store:
                all_rules.extend(_book_store[bid].get('rules', []))

        matched = _match_rules_to_chart(all_rules, positions)

        # Annotate with book name
        book_map = {bid: _book_store[bid].get('filename', bid) for bid in book_ids if bid in _book_store}
        for rule in matched:
            bid = rule.get('book_id')
            if bid:
                rule['book_name'] = book_map.get(bid, bid)

        return jsonify({
            'matched':     matched,
            'total_rules': len(all_rules),
            'match_count': len(matched),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

@app.route('/discuss')
def discuss_page():
    return render_template('discuss.html')

@app.route('/rule-library')
def rule_library_page():
    return render_template('rule_library.html')

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static',    exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
