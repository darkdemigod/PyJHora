
from flask import Flask, render_template, request, jsonify
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jhora.horoscope.main import Horoscope
from jhora.panchanga import drik

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PyJHora Web Interface</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; }
            input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            .result { margin-top: 20px; padding: 20px; background-color: #f9f9f9; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PyJHora - Vedic Astrology Calculator</h1>
            <form id="horoscopeForm">
                <div class="form-group">
                    <label for="place">Place (e.g., Chennai,IN):</label>
                    <input type="text" id="place" name="place" value="Chennai,IN" required>
                </div>
                
                <div class="form-group">
                    <label for="date">Date of Birth:</label>
                    <input type="date" id="date" name="date" value="1996-12-07" required>
                </div>
                
                <div class="form-group">
                    <label for="time">Time of Birth (HH:MM):</label>
                    <input type="time" id="time" name="time" value="10:34" required>
                </div>
                
                <button type="submit">Generate Horoscope</button>
            </form>
            
            <div id="result" class="result" style="display: none;">
                <h2>Horoscope Results</h2>
                <div id="resultContent"></div>
            </div>
        </div>

        <script>
            document.getElementById('horoscopeForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                try {
                    const response = await fetch('/calculate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('resultContent').innerHTML = formatResult(result.data);
                        document.getElementById('result').style.display = 'block';
                    } else {
                        alert('Error: ' + result.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            
            function formatResult(data) {
                let html = '<h3>Calendar Information</h3><ul>';
                for (const [key, value] of Object.entries(data.calendar_info)) {
                    html += `<li><strong>${key}:</strong> ${value}</li>`;
                }
                html += '</ul>';
                
                html += '<h3>Chart Information</h3>';
                html += '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px;">';
                
                for (let i = 0; i < 12; i++) {
                    const house = data.chart_info[i] || '';
                    html += `<div style="border: 1px solid #ccc; padding: 10px; min-height: 80px; background: #f9f9f9;">
                        <strong>House ${i + 1}</strong><br>
                        ${house.replace(/\\n/g, '<br>')}
                    </div>`;
                }
                
                html += '</div>';
                return html;
            }
        </script>
    </body>
    </html>
    '''

@app.route('/calculate', methods=['POST'])
def calculate_horoscope():
    try:
        data = request.get_json()
        
        # Parse the input data
        place_str = data['place']
        date_str = data['date']  # Format: YYYY-MM-DD
        time_str = data['time']  # Format: HH:MM
        
        # Parse date
        year, month, day = map(int, date_str.split('-'))
        dob = drik.Date(year, month, day)
        
        # Parse time
        hour, minute = map(int, time_str.split(':'))
        birth_time = f"{hour:02d}:{minute:02d}:00"
        
        # Create horoscope object
        horoscope = Horoscope(
            place_with_country_code=place_str,
            date_in=dob,
            birth_time=birth_time
        )
        
        # Get calendar and chart information
        calendar_info = horoscope.calendar_info
        horo_info, chart_info, asc_info = horoscope.get_horoscope_information_for_chart(chart_index=0)
        
        return jsonify({
            'success': True,
            'data': {
                'calendar_info': calendar_info,
                'chart_info': chart_info,
                'ascendant_house': asc_info
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
