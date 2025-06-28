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
from jhora.ui.panchangam import PanchangaInfoDialog

app = Flask(__name__)
app.secret_key = 'jhora_secret_key_2024'

# Initialize language settings
utils.set_language(const.available_languages['English'])

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

        # Format the response
        result = {
            'place': f"{place_name} ({latitude:.4f}°, {longitude:.4f}°)",
            'date': date_str,
            'time': time_str,
            'sunrise': sunrise[1] if len(sunrise) > 1 else 'N/A',
            'sunset': sunset[1] if len(sunset) > 1 else 'N/A',
            'moonrise': moonrise[1] if len(moonrise) > 1 else 'N/A',
            'moonset': moonset[1] if len(moonset) > 1 else 'N/A',
            'tithi': f"{utils.TITHI_LIST[tithi_info[0]-1]} ({utils.TITHI_DEITIES[tithi_info[0]-1]})",
            'nakshatra': f"{utils.NAKSHATRA_LIST[nakshatra_info[0]-1]} - Pada {nakshatra_info[1]}",
            'yoga': utils.YOGAM_LIST[yoga_info[0]-1],
            'karana': utils.KARANA_LIST[karana_info[0]-1],
            'rasi': utils.RAASI_LIST[rasi_info[0]-1],
            'vaara': utils.DAYS_LIST[drik.vaara(jd)]
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
        time_parts = time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0

        year, month, day = date_obj.year, date_obj.month, date_obj.day

        # Create place and calculate julian day
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((year, month, day), (hour, minute, second))

        # Calculate planetary positions
        planet_positions = charts.rasi_chart(jd, place)
        navamsa_positions = charts.navamsa_chart(jd, place)

        # Calculate ascendant
        ascendant = charts.ascendant(jd, place)

        # Format planetary positions
        planets_info = {}
        for planet, (house, longitude) in planet_positions:
            planets_info[utils.PLANET_NAMES[planet]] = {
                'house': house + 1,  # Convert to 1-based indexing
                'sign': utils.RAASI_LIST[house],
                'longitude': f"{longitude:.2f}°"
            }

        # Add ascendant info
        asc_house, asc_long = ascendant
        planets_info['Ascendant'] = {
            'house': asc_house + 1,
            'sign': utils.RAASI_LIST[asc_house],
            'longitude': f"{asc_long:.2f}°"
        }

        # Calculate yogas
        yoga_results = []
        try:
            yogas = yoga.get_all_yogas(jd, place)
            for y in yogas[:10]:  # Limit to first 10 yogas
                yoga_results.append({
                    'name': y[0],
                    'description': y[1] if len(y) > 1 else ''
                })
        except:
            pass

        result = {
            'planets': planets_info,
            'yogas': yoga_results,
            'chart_data': {
                'rasi': planet_positions,
                'navamsa': navamsa_positions
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

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
            dhasa_periods = vimsottari.vimsottari_dhasa_bhukthi(jd, place)

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

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    app.run(host='0.0.0.0', port=5000, debug=True)