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
- `templates/horoscope.html` — 4-tab chart calculator (Planets, Yogas, Strengths, Dashas)
- `templates/interpret.html` — Deep paragraph-level interpretation page
- `templates/pdf_toolkit.html` — PDF upload + rule extraction page
- `templates/learning.html` — Book-to-chart rule matching + pattern detection
- `src/jhora/` — PyJHora library modules (charts, drik, utils, yoga, strength, etc.)
- `uploads/` — PDF file storage

## API Endpoints
### Chart
- `POST /api/horoscope` — Full chart: planets, Raja Yogas, Shad Bala matrix, doshas. Returns `chart_id` for caching.
- `POST /api/divisional` — Divisional (varga) charts
- `POST /api/dhasa` — Vimsottari dasha. Supports `tree:true` for 3-level Maha→Antar→Pratyantara tree
- `POST /api/panchanga` — Daily panchanga
- `POST /api/transit` — Current transits
- `POST /api/compatibility` — Guna Milan / Kundali matching

### Interpretation
- `POST /api/interpret` — Deep paragraph-level interpretation. Accepts `chart_id` or birth data + optional `book_id`
- `GET /api/interpret/<chart_id>` — Re-interpret cached chart, optionally with `?book_id=`

### PDF / Books
- `POST /api/pdf/upload` — Upload PDF book, extract text + semantic chunks + rules
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
- `/horoscope` — 4-tab Chart Calculator
- `/divisional` — Divisional Charts
- `/dasha` — Dhasa (legacy)
- `/compatibility` — Kundali Matching
- `/prashna` — KP Prashna
- `/transit` — Current Transits
- `/predictions` — V4 Predictions
- `/calendar` — Ephemeris Calendar
- `/interpret` — Deep Interpreter (NEW)
- `/pdf-toolkit` — PDF Book Upload + Rule Extraction (NEW)
- `/learning` — Pattern Detection + Rule Matching (NEW)

## Key Data Structures
### parse_birth_data()
Accepts EITHER `{year, month, day, hour, minute, latitude, longitude, timezone}` OR `{date, time, latitude, longitude, timezone}`.

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
- `_compute_pratyantara(start_str, end_str)` — Proportional 3rd-level dasha subdivision
- `_score_astro_relevance(text)` — Score text for astrological keyword density
- `_extract_rules(text, min_score)` — Extract astrological rules from book text (sentence-level)
- `_match_rules_to_chart(rules, positions)` — Score rules against actual planet positions
- `_deep_interpret(positions, raja_yogas, doshas, shad_bala, matched_rules)` — Generate paragraph-level interpretation

## Dependencies
- flask, pypdf (6.10.2), werkzeug
- PyJHora library (local in src/jhora/)
- Standard: uuid, re, datetime, timedelta, os

## Constants (in app.py)
- `DASHA_YEARS_BY_ID` — [7,20,6,10,7,18,16,19,17] (Ketu→Mercury)
- `SHAD_BALA_LABELS` — 9 component names
- `SHAD_BALA_PLANETS` — 7 planets Sun–Saturn
- `ASTRO_KEYWORDS` — Dict of category→keyword lists for rule scoring
- `RASI_SIGNS` — 12 sign names
