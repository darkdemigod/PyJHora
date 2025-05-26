
#!/usr/bin/env python3
"""
JHora Web Interface
A Flask-based web application for Vedic Astrology calculations
"""

import sys
import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from jhora.panchanga import drik
    from jhora.horoscope.chart import charts
    from jhora.horoscope import main as horo_main
    from jhora import const, utils
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure PyJHora is properly installed")
    sys.exit(1)

app = Flask(__name__)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/panchanga', methods=['POST'])
def get_panchanga():
    """Get panchanga information for given date and place"""
    try:
        data = request.json
        
        # Extract parameters
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        time_str = data.get('time', '12:00:00')
        place_name = data.get('place', 'Chennai,IN')
        latitude = float(data.get('latitude', 13.0827))
        longitude = float(data.get('longitude', 80.2707))
        timezone = float(data.get('timezone', 5.5))
        
        # Parse date and time
        date_obj = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
        
        # Create place tuple
        place = (place_name, latitude, longitude, timezone)
        
        # Calculate Julian day
        jd = utils.julian_day_number(date_obj, timezone)
        
        # Get panchanga information
        panchanga_info = {}
        
        # Basic calculations
        panchanga_info['sunrise'] = drik.sunrise(jd, place)[1]
        panchanga_info['sunset'] = drik.sunset(jd, place)[1]
        panchanga_info['tithi'] = drik.tithi(jd, place)
        panchanga_info['nakshatra'] = drik.nakshatra(jd, place)
        panchanga_info['yoga'] = drik.yoga(jd, place)
        panchanga_info['karana'] = drik.karana(jd, place)
        panchanga_info['vaara'] = drik.vaara(jd)
        
        # Moon phase
        panchanga_info['moon_phase'] = drik.lunar_month(jd, place)
        
        return jsonify({
            'success': True,
            'data': panchanga_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/horoscope', methods=['POST'])
def get_horoscope():
    """Get horoscope chart information"""
    try:
        data = request.json
        
        # Extract birth details
        birth_date = data.get('birth_date')
        birth_time = data.get('birth_time')
        birth_place = data.get('birth_place')
        latitude = float(data.get('latitude', 13.0827))
        longitude = float(data.get('longitude', 80.2707))
        timezone = float(data.get('timezone', 5.5))
        
        # Parse birth date and time
        birth_datetime = datetime.strptime(f"{birth_date} {birth_time}", '%Y-%m-%d %H:%M:%S')
        
        # Create place tuple
        place = (birth_place, latitude, longitude, timezone)
        
        # Calculate horoscope
        jd = utils.julian_day_number(birth_datetime, timezone)
        
        # Get planet positions
        planet_positions = charts.rasi_chart(jd, place)
        
        # Get houses
        asc_house = charts.ascendant(jd, place)
        
        # Get navamsa
        navamsa_positions = charts.navamsa_chart(jd, place)
        
        return jsonify({
            'success': True,
            'data': {
                'planet_positions': planet_positions,
                'ascendant': asc_house,
                'navamsa': navamsa_positions
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/compatibility', methods=['POST'])
def get_compatibility():
    """Get marriage compatibility"""
    try:
        data = request.json
        
        # Extract details for boy and girl
        boy_star = data.get('boy_star')
        girl_star = data.get('girl_star')
        boy_pada = data.get('boy_pada', 1)
        girl_pada = data.get('girl_pada', 1)
        
        # Calculate compatibility (simplified)
        compatibility_score = utils.calculate_compatibility(boy_star, girl_star, boy_pada, girl_pada)
        
        return jsonify({
            'success': True,
            'data': {
                'compatibility_score': compatibility_score,
                'recommendation': 'Compatible' if compatibility_score > 18 else 'Not Compatible'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Create templates directory and basic HTML template
@app.before_first_request
def create_templates():
    """Create templates directory and files if they don't exist"""
    templates_dir = os.path.join(current_dir, 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
        # Create basic index.html
        index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JHora 4.5.0 - Vedic Astrology</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #8B4513; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { background-color: #8B4513; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        button:hover { background-color: #A0522D; }
        .result { margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background-color: #ddd; border: none; cursor: pointer; }
        .tab.active { background-color: #8B4513; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕉️ JHora 4.5.0 - Vedic Astrology</h1>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('panchanga')">Panchanga</button>
            <button class="tab" onclick="showTab('horoscope')">Horoscope</button>
            <button class="tab" onclick="showTab('compatibility')">Compatibility</button>
        </div>
        
        <!-- Panchanga Tab -->
        <div id="panchanga" class="tab-content active">
            <h2>Daily Panchanga</h2>
            <form id="panchangaForm">
                <div class="form-group">
                    <label for="date">Date:</label>
                    <input type="date" id="date" name="date" required>
                </div>
                <div class="form-group">
                    <label for="time">Time:</label>
                    <input type="time" id="time" name="time" value="12:00" required>
                </div>
                <div class="form-group">
                    <label for="place">Place:</label>
                    <input type="text" id="place" name="place" value="Chennai,IN" required>
                </div>
                <div class="form-group">
                    <label for="latitude">Latitude:</label>
                    <input type="number" id="latitude" name="latitude" value="13.0827" step="0.0001" required>
                </div>
                <div class="form-group">
                    <label for="longitude">Longitude:</label>
                    <input type="number" id="longitude" name="longitude" value="80.2707" step="0.0001" required>
                </div>
                <button type="submit">Calculate Panchanga</button>
            </form>
            <div id="panchangaResult" class="result" style="display:none;"></div>
        </div>
        
        <!-- Horoscope Tab -->
        <div id="horoscope" class="tab-content">
            <h2>Birth Chart</h2>
            <form id="horoscopeForm">
                <div class="form-group">
                    <label for="birth_date">Birth Date:</label>
                    <input type="date" id="birth_date" name="birth_date" required>
                </div>
                <div class="form-group">
                    <label for="birth_time">Birth Time:</label>
                    <input type="time" id="birth_time" name="birth_time" required>
                </div>
                <div class="form-group">
                    <label for="birth_place">Birth Place:</label>
                    <input type="text" id="birth_place" name="birth_place" value="Chennai,IN" required>
                </div>
                <button type="submit">Generate Chart</button>
            </form>
            <div id="horoscopeResult" class="result" style="display:none;"></div>
        </div>
        
        <!-- Compatibility Tab -->
        <div id="compatibility" class="tab-content">
            <h2>Marriage Compatibility</h2>
            <form id="compatibilityForm">
                <div class="form-group">
                    <label for="boy_star">Boy's Nakshatra:</label>
                    <input type="text" id="boy_star" name="boy_star" required>
                </div>
                <div class="form-group">
                    <label for="girl_star">Girl's Nakshatra:</label>
                    <input type="text" id="girl_star" name="girl_star" required>
                </div>
                <button type="submit">Check Compatibility</button>
            </form>
            <div id="compatibilityResult" class="result" style="display:none;"></div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
        
        // Set today's date as default
        document.getElementById('date').value = new Date().toISOString().split('T')[0];
        document.getElementById('birth_date').value = new Date().toISOString().split('T')[0];
        
        // Handle form submissions
        document.getElementById('panchangaForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/panchanga', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('panchangaResult');
                
                if (result.success) {
                    resultDiv.innerHTML = '<h3>Panchanga Results:</h3>' + 
                        JSON.stringify(result.data, null, 2).replace(/\\n/g, '<br>');
                } else {
                    resultDiv.innerHTML = '<h3>Error:</h3>' + result.error;
                }
                
                resultDiv.style.display = 'block';
            } catch (error) {
                console.error('Error:', error);
            }
        });
        
        // Similar handlers for other forms...
    </script>
</body>
</html>
        """
        
        with open(os.path.join(templates_dir, 'index.html'), 'w') as f:
            f.write(index_html)

if __name__ == '__main__':
    print("Starting JHora Web Application...")
    print("Visit http://0.0.0.0:5000 to access the application")
    app.run(host='0.0.0.0', port=5000, debug=True)
