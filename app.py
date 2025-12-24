from flask import Flask, render_template, request, jsonify, send_file
import sys
import os
import io
import base64
from datetime import datetime, date
import json

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import JHora modules
from jhora import utils, const
from jhora.panchanga import drik
from jhora.horoscope import main as horo_main
from jhora.horoscope.chart import charts, ashtakavarga, yoga, dosha, strength
from jhora.horoscope.match import compatibility
from jhora.horoscope.dhasa.graha import vimsottari
from jhora.vedic_v4_predictor import PredictionEngine

app = Flask(__name__)
app.secret_key = 'jhora_secret_key_2024'

# Initialize language settings
utils.set_language(const.available_languages['English'])

# Initialize V4 Prediction Engine
prediction_engine = PredictionEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/panchanga')
def panchanga_page():
    return render_template('panchanga.html')

@app.route('/horoscope')
def horoscope_page():
    return render_template('horoscope.html')

@app.route('/compatibility')
def compatibility_page():
    return render_template('compatibility.html')

@app.route('/dhasa')
def dhasa_page():
    return render_template('dhasa.html')

@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/api/panchanga', methods=['POST'])
def calculate_panchanga():
    try:
        data = request.json
        date_str = data.get('date')
        time_str = data.get('time', '12:00')
        place_name = data.get('place', 'Chennai,IN')
        latitude = float(data.get('latitude', 13.0878))
        longitude = float(data.get('longitude', 80.2785))
        timezone = float(data.get('timezone', 5.5))

        # Parse date and time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()

        year, month, day = date_obj.year, date_obj.month, date_obj.day
        hour, minute = time_obj.hour, time_obj.minute

        # Create place and calculate julian day
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((year, month, day), (hour, minute, 0))

        # Calculate panchanga information
        sunrise = drik.sunrise(jd, place)
        sunset = drik.sunset(jd, place)
        moonrise = drik.moonrise(jd, place)
        moonset = drik.moonset(jd, place)

        tithi_info = drik.tithi(jd, place)
        nakshatra_info = drik.nakshatra(jd, place)
        yoga_info = drik.yogam(jd, place)
        karana_info = drik.karana(jd, place)
        rasi_info = drik.raasi(jd, place)

        # Safely extract time values
        sunrise_time = sunrise[1] if (isinstance(sunrise, (tuple, list)) and len(sunrise) > 1) else 'N/A'
        sunset_time = sunset[1] if (isinstance(sunset, (tuple, list)) and len(sunset) > 1) else 'N/A'
        moonrise_time = moonrise[1] if (isinstance(moonrise, (tuple, list)) and len(moonrise) > 1) else 'N/A'
        moonset_time = moonset[1] if (isinstance(moonset, (tuple, list)) and len(moonset) > 1) else 'N/A'

        # Safely extract panchanga values
        tithi_name = utils.TITHI_LIST[int(tithi_info[0])-1] if (isinstance(tithi_info, (tuple, list)) and len(tithi_info) > 0) else 'Unknown'
        tithi_deity = utils.TITHI_DEITIES[int(tithi_info[0])-1] if (isinstance(tithi_info, (tuple, list)) and len(tithi_info) > 0) else 'Unknown'
        
        nakshatra_name = utils.NAKSHATRA_LIST[int(nakshatra_info[0])-1] if (isinstance(nakshatra_info, (tuple, list)) and len(nakshatra_info) > 0) else 'Unknown'
        nakshatra_pada = int(nakshatra_info[1]) if (isinstance(nakshatra_info, (tuple, list)) and len(nakshatra_info) > 1) else 1
        
        yoga_name = utils.YOGAM_LIST[int(yoga_info[0])-1] if (isinstance(yoga_info, (tuple, list)) and len(yoga_info) > 0) else 'Unknown'
        karana_name = utils.KARANA_LIST[int(karana_info[0])-1] if (isinstance(karana_info, (tuple, list)) and len(karana_info) > 0) else 'Unknown'
        rasi_name = utils.RAASI_LIST[int(rasi_info[0])-1] if (isinstance(rasi_info, (tuple, list)) and len(rasi_info) > 0) else 'Unknown'
        
        vaara_index = int(drik.vaara(jd)) % 7 if drik.vaara(jd) is not None else 0
        vaara_name = utils.DAYS_LIST[vaara_index]

        # Format the response
        result = {
            'place': f"{place_name} ({latitude:.4f}°, {longitude:.4f}°)",
            'date': date_str,
            'time': time_str,
            'sunrise': str(sunrise_time),
            'sunset': str(sunset_time),
            'moonrise': str(moonrise_time),
            'moonset': str(moonset_time),
            'tithi': f"{tithi_name} ({tithi_deity})",
            'nakshatra': f"{nakshatra_name} - Pada {nakshatra_pada}",
            'yoga': yoga_name,
            'karana': karana_name,
            'rasi': rasi_name,
            'vaara': vaara_name
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/horoscope', methods=['POST'])
def calculate_horoscope():
    try:
        data = request.json
        date_str = data.get('date')
        time_str = data.get('time', '12:00:00')
        place_name = data.get('place', 'Chennai,IN')
        latitude = float(data.get('latitude', 13.0878))
        longitude = float(data.get('longitude', 80.2785))
        timezone = float(data.get('timezone', 5.5))

        # Parse date and time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_parts = str(time_str).split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        second = int(time_parts[2]) if len(time_parts) > 2 else 0

        year, month, day = date_obj.year, date_obj.month, date_obj.day

        # Create place and calculate julian day
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((year, month, day), (hour, minute, second))

        # Get ascendant
        ascendant_data = drik.ascendant(jd, place)
        asc_house = int(ascendant_data[0]) if (isinstance(ascendant_data, (tuple, list)) and len(ascendant_data) > 0) else 0
        asc_long = float(ascendant_data[1]) if (isinstance(ascendant_data, (tuple, list)) and len(ascendant_data) > 1) else 0.0

        # Build basic chart info
        planets_info = {
            'Ascendant': {
                'house': asc_house + 1,
                'sign': utils.RAASI_LIST[asc_house % 12],
                'longitude': f"{asc_long:.2f}°"
            }
        }

        result = {
            'status': 'success',
            'chart': {
                'date': date_str,
                'time': time_str,
                'location': place_name,
                'coordinates': f"{latitude:.4f}°, {longitude:.4f}°"
            },
            'planets': planets_info,
            'yogas': [],
            'message': 'Chart calculated successfully'
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

@app.route('/api/compatibility', methods=['POST'])
def calculate_compatibility():
    try:
        data = request.json
        boy_star = int(data.get('boy_star', 1))
        boy_pada = int(data.get('boy_pada', 1))
        girl_star = int(data.get('girl_star', 1))
        girl_pada = int(data.get('girl_pada', 1))

        # Calculate compatibility
        comp = compatibility.Ashtakoota(boy_star, boy_pada, girl_star, girl_pada)
        ettu_porutham, total_score, naalu_porutham = comp.compatibility_score()

        # Format results
        porutham_names = [
            'Varna Porutham', 'Vasya Porutham', 'Gana Porutham', 
            'Nakshatra Porutham', 'Yoni Porutham', 'Rasi Adhipati Porutham',
            'Rasi Porutham', 'Nadi Porutham'
        ]

        naalu_porutham_names = [
            'Mahendra Porutham', 'Vedha Porutham', 
            'Rajju Porutham', 'Sthree Dheerga Porutham'
        ]

        results = []
        max_scores = [1, 2, 6, 4, 4, 5, 7, 8]  # Maximum scores for each porutham

        for i, (score, max_score) in enumerate(zip(ettu_porutham, max_scores)):
            results.append({
                'name': porutham_names[i],
                'score': score,
                'max_score': max_score,
                'percentage': round((score / max_score) * 100, 1)
            })

        for i, result in enumerate(naalu_porutham):
            results.append({
                'name': naalu_porutham_names[i],
                'score': 'Yes' if result else 'No',
                'max_score': 'Yes',
                'percentage': 100 if result else 0
            })

        overall_percentage = round((total_score / compatibility.max_compatibility_score) * 100, 1)

        return jsonify({
            'results': results,
            'total_score': total_score,
            'max_total': compatibility.max_compatibility_score,
            'overall_percentage': overall_percentage,
            'boy_star': utils.NAKSHATRA_LIST[boy_star - 1],
            'girl_star': utils.NAKSHATRA_LIST[girl_star - 1]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/dhasa', methods=['POST'])
def calculate_dhasa():
    try:
        data = request.json
        date_str = data.get('date')
        time_str = data.get('time', '12:00:00')
        place_name = data.get('place', 'Chennai,IN')
        latitude = float(data.get('latitude', 13.0878))
        longitude = float(data.get('longitude', 80.2785))
        timezone = float(data.get('timezone', 5.5))
        dhasa_type = data.get('dhasa_type', 'vimsottari')

        # Parse date and time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_parts = time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0

        year, month, day = date_obj.year, date_obj.month, date_obj.day

        # Create place and calculate julian day
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((year, month, day), (hour, minute, second))

        # Calculate dhasa periods
        if dhasa_type == 'vimsottari':
            dhasa_periods = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)

            results = []
            for period in dhasa_periods[:20]:  # Limit to first 20 periods
                start_date = utils.jd_to_gregorian(period[1])
                end_date = utils.jd_to_gregorian(period[2])

                results.append({
                    'planet': utils.PLANET_NAMES[period[0]],
                    'start_date': f"{start_date[2]:02d}-{start_date[1]:02d}-{start_date[0]}",
                    'end_date': f"{end_date[2]:02d}-{end_date[1]:02d}-{end_date[0]}",
                    'duration_years': round((period[2] - period[1]) / 365.25, 2)
                })
        else:
            results = [{'error': 'Dhasa type not implemented yet'}]

        return jsonify({'periods': results, 'dhasa_type': dhasa_type})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/predictions', methods=['POST'])
def get_predictions():
    """V4.0 Advanced predictions: Dasha, Marriage, Doshas, Yogas"""
    try:
        data = request.json
        birth_date = data.get('birth_date', '2000-01-01T12:00:00')
        
        chart_data = {
            'lagna_sign': int(data.get('lagna_sign', 1)),
            'moon_sign': int(data.get('moon_sign', 1)),
            'moon_nakshatra': int(data.get('moon_nakshatra', 1)),
            'venus_sign': int(data.get('venus_sign', 2)),
            'mars_sign': int(data.get('mars_sign', 3)),
            'mars_house': int(data.get('mars_house', 1)),
            'jupiter_sign': int(data.get('jupiter_sign', 5)),
            'mercury_sign': int(data.get('mercury_sign', 4)),
            'saturn_sign': int(data.get('saturn_sign', 7)),
        }
        
        report = prediction_engine.generate_prediction_report(chart_data, birth_date)
        return jsonify(report)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Disable Flask reloader which can cause port conflicts
    app.run(host='0.0.0.0', port=5000, debug=False)