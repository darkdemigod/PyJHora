# PyJHora — Vedic Astrology OS (ASTRO_OS v4)

## Overview
Full Vedic astrology web application built on PyJHora, served via Flask on port 5000. Jinja2 templates + vanilla JS frontend with dark theme.

## Architecture
- **Backend**: Flask (app.py), Python 3.11, PyJHora library
- **Frontend**: Jinja2 templates + vanilla JS, no React/TypeScript
- **Port**: 5000
- **Start**: `bash start_server.sh`

## Key Files
- `app.py` — Main Flask app, all API endpoints and page routes
- `templates/base.html` — Shared nav + CSS design system
- `templates/horoscope.html` — 5-tab chart calculator (Planets, Houses, Yogas, Strengths, Dashas)
- `templates/interpret.html` — Deep paragraph-level interpretation page
- `templates/pdf_toolkit.html` — PDF upload + rule extraction with formula tags
- `templates/learning.html` — Book-to-chart rule matching + pattern detection
- `src/jhora/` — PyJHora library modules (charts, drik, utils, yoga, strength, etc.)
- `uploads/` — PDF file storage

## API Endpoints
### Chart
- `POST /api/horoscope` — Full chart: planets (with house, nakshatra, dignity, house_type), Raja Yogas, Shad Bala matrix, doshas. Returns `chart_id` for caching.
- `POST /api/divisional` — Divisional (varga) charts
- `POST /api/dhasa` — Vimsottari dasha. Supports `tree:true` for 3-level Maha→Antar→Pratyantara tree
- `POST /api/panchanga` — Daily panchanga
- `POST /api/transit` — Current transits
- `POST /api/compatibility` — Guna Milan / Kundali matching

### Interpretation
- `POST /api/interpret` — Deep paragraph-level interpretation. Accepts `chart_id` or birth data + optional `book_id`
- `GET /api/interpret/<chart_id>` — Re-interpret cached chart, optionally with `?book_id=`

### PDF / Books
- `POST /api/pdf/upload` — Upload PDF book, extract text + semantic chunks + structured rules with formula tags
- `GET /api/books` — List all uploaded books
- `GET /api/books/<id>/parse-rules` — Re-parse rules with configurable `?min_score=`
- `DELETE /api/books/<id>` — Delete book

### Other
- `POST /api/prashna` — KP Prashna horary
- `POST /api/predict` — V4 predictor
- `POST /api/astromap` — Astrocartography
- `GET /api/compatibility` — Status

## Page Routes
- `/` — Dashboard (engine status)
- `/panchanga` — Daily Panchanga
- `/horoscope` — 5-tab Chart Calculator (Planets | Houses | Yogas | Strengths | Dashas)
- `/divisional` — Divisional Charts
- `/dasha` — Dhasa (legacy)
- `/compatibility` — Kundali Matching
- `/prashna` — KP Prashna
- `/transit` — Current Transits
- `/predictions` — V4 Predictions
- `/calendar` — Ephemeris Calendar
- `/interpret` — Deep Interpreter
- `/pdf-toolkit` — PDF Book Upload + Rule Extraction
- `/learning` — Pattern Detection + Rule Matching

## Key Data Structures

### Planet object (from /api/horoscope `planets` array)
```json
{
  "id": 0,
  "name": "Sun",
  "rasi": 8,
  "sign": "Sagittarius",
  "house": 1,
  "house_type": "kendra",
  "lord": "Jupiter",
  "dignity": "neutral",
  "nakshatra": "Purva Ashadha",
  "nak_pada": 3,
  "nak_lord": "Venus",
  "lon_in_sign": 10.34,
  "longitude": 250.34
}
```
`dignity` values: `exalted | debilitated | moolatrikona | own | neutral`
`house_type` values: `kendra | trikona | dusthana | upachaya | neutral`

### Rule object (from /api/books/<id>/parse-rules `all_rules` array)
```json
{
  "text": "Jupiter in Cancer gives great fortune...",
  "score": 8,
  "categories": ["yoga", "house"],
  "planets": ["Jupiter"],
  "signs": ["Cancer"],
  "houses": [9],
  "formulas": [
    {"type": "planet_in_sign", "planet": "Jupiter", "sign": "Cancer"},
    {"type": "planet_in_house", "planet": "Jupiter", "house": 9}
  ]
}
```
Formula types: `planet_in_sign | planet_in_house | lord_transfer | conjunction | aspect | exaltation | debilitation | retrograde | yoga_name | special_house_type`

### Shad Bala
`strength.shad_bala(jd, place)` → list of 9 component rows × 7 planets (Sun–Saturn only).
Matrix format: `sb[component_idx][planet_idx]`. Labels in `SHAD_BALA_LABELS`, planets in `SHAD_BALA_PLANETS`.

### Dasha Tree
`vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)` → `(start_info, [(maha_id, antar_id, date_str), ...])`
With `tree:true`, returns `{tree: [{planet, start_date, antar: [{planet, start_date, end_date, pratyantara:[...]}]}]}`

### Raja Yogas
`raja_yoga.get_raja_yoga_details(jd, place)` → `(dict, ...)` where dict maps `yoga_name → [pairs, name, description, effect]`

## In-memory Caches
- `_chart_cache` — Up to 200 charts keyed by 12-char UUID `chart_id`
- `_book_store` — Uploaded books: `{book_id: {filename, pages, text, chunks, rules, save_path}}`

## Helper Functions
- `get_planet_positions(jd, place)` — 2-pass algorithm: finds Lagna rasi first, then computes bhava (house = ((planet_rasi - lagna_rasi) % 12) + 1) for all planets. Returns full planet dicts with nakshatra, dignity, house_type.
- `_extract_formulas_from_text(text)` — Extracts structured formula objects from a sentence using FORMULA_PATTERNS (10 compiled regex patterns)
- `_evaluate_formula(formula, positions)` — Returns True if a formula applies to the chart (planet_in_sign check, lord_transfer via SIGN_LORDS, conjunction via equal house, aspect via SPECIAL_ASPECTS)
- `_extract_rules(text, min_score)` — Extracts rules with formula tags, deduplication, multi-category tagging
- `_match_rules_to_chart(rules, positions)` — Formula-level matching (5× weight) + keyword fallback; skips rules with formulas that all fail
- `_house_lord_analysis(positions)` — Builds 12-row bhava analysis with lord placement quality
- `_deep_interpret(positions, raja_yogas, doshas, shad_bala, matched_rules)` — 9-section rich interpretation: lagna, dignity, house lords, kendra-trikona yoga, conjunctions, raja yogas, shad bala, doshas, classical rules
- `_compute_pratyantara(start_str, end_str)` — Proportional 3rd-level dasha subdivision

## Constants (in app.py)
- `DASHA_YEARS_BY_ID` — [6,10,7,17,16,20,19,18,7] (Sun→Ketu, 120yr total)
- `SHAD_BALA_LABELS` — 9 component names
- `SHAD_BALA_PLANETS` — 7 planets Sun–Saturn
- `RASI_SIGNS` — 12 sign names
- `SIGN_LORDS` — Sign→ruling planet dict
- `EXALTATION_SIGN`, `DEBILITATION_SIGN`, `OWN_SIGNS`, `MOOLATRIKONA` — Dignity lookup dicts
- `NAKSHATRA_NAMES` — 27 nakshatra names
- `NAKSHATRA_LORDS` — 27 nakshatra lords (Ketu/Venus/Sun/Moon/Mars/Rahu/Jupiter/Saturn/Mercury × 3)
- `HOUSE_KARKA` — House 1–12 significations
- `KENDRA_HOUSES`, `TRIKONA_HOUSES`, `DUSTHANA_HOUSES`, `UPACHAYA_HOUSES` — House classification sets
- `SPECIAL_ASPECTS` — Special aspects beyond 7th (Mars:4,8; Jupiter:5,9; Saturn:3,10; Rahu/Ketu:5,9)
- `ASTRO_KEYWORDS` — Expanded 8-category keyword dict for relevance scoring
- `FORMULA_PATTERNS` — 10 compiled regex patterns for structured rule extraction

## Dependencies
- flask, pypdf (6.10.2), werkzeug
- PyJHora library (local in src/jhora/)
- Standard: uuid, re, datetime, timedelta, os
