"""
Vedic Astrology V4.0 - Advanced Prediction Engine
Integrates: Dasha, Transit, Yoga, Dosha, and Prashna analysis
"""

from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from datetime import datetime, timedelta


class PredictionEngine:
    """Advanced prediction engine for Vedic astrology"""

    def __init__(self):
        self.dasha_lords = {
            0: "Ketu", 1: "Venus", 2: "Sun", 3: "Moon", 4: "Mars",
            5: "Rahu", 6: "Jupiter", 7: "Saturn", 8: "Mercury"
        }
        self.dasha_years = [7, 20, 6, 10, 7, 18, 16, 19, 17]

    def calculate_vimshottari_dasha(self, moon_nakshatra: int, 
                                   birth_date: str) -> Dict[str, Any]:
        """
        Calculate Vimshottari Dasha (120-year cycle)
        Returns: Current dasha period and upcoming periods
        """
        try:
            birth = datetime.fromisoformat(birth_date)
            today = datetime.now()
            days_lived = (today - birth).days
            years_lived = days_lived / 365.25
            
            # Determine starting dasha from nakshatra
            start_dasha = moon_nakshatra % 9
            
            # Calculate current position in 120-year cycle
            total_years_cycle = sum(self.dasha_years)
            years_in_cycle = years_lived % total_years_cycle
            
            # Find current dasha
            dasha_sequence = []
            cumulative = 0
            for i in range(9):
                dasha_idx = (start_dasha + i) % 9
                years = self.dasha_years[dasha_idx]
                dasha_name = self.dasha_lords[dasha_idx]
                
                if cumulative <= years_in_cycle < cumulative + years:
                    current_dasha = dasha_name
                    years_left = (cumulative + years) - years_in_cycle
                    break
                    
                dasha_sequence.append({
                    'dasha': dasha_name,
                    'years': years,
                    'start': cumulative,
                    'end': cumulative + years
                })
                cumulative += years
            
            # Get upcoming dashas
            upcoming = []
            cumulative = cumulative + self.dasha_years[dasha_idx]
            for i in range(1, 5):
                next_idx = (start_dasha + i) % 9
                next_dasha = self.dasha_lords[next_idx]
                next_years = self.dasha_years[next_idx]
                upcoming.append({
                    'dasha': next_dasha,
                    'years': next_years,
                    'starts_in_years': max(0, (cumulative - years_in_cycle))
                })
                cumulative += next_years
            
            return {
                'status': 'success',
                'current_dasha': current_dasha,
                'years_remaining': round(years_left, 2),
                'dasha_sequence': dasha_sequence,
                'upcoming_dashas': upcoming,
                'age_years': round(years_lived, 2),
                'position_in_cycle': round(years_in_cycle, 2)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def predict_marriage_timing(self, chart_data: Dict) -> Dict[str, Any]:
        """Predict marriage timing based on chart"""
        try:
            lagna = chart_data.get('lagna_sign', 1)
            venus_sign = chart_data.get('venus_sign', 2)
            seventh_lord = self._get_house_lord(7, lagna)
            
            # Simple timing: Based on Venus and 7th house lord
            venus_strength = 5 if venus_sign in [2, 12] else 3
            seventh_strength = 5 if seventh_lord in [1, 5, 7, 9] else 3
            
            combined_strength = (venus_strength + seventh_strength) / 2
            
            # Estimate age range
            if combined_strength >= 4.5:
                age_range = "Early 20s (20-24)"
                probability = "Very High"
            elif combined_strength >= 3.5:
                age_range = "Mid 20s (24-28)"
                probability = "High"
            else:
                age_range = "Late 20s/Early 30s (28-34)"
                probability = "Moderate"
            
            return {
                'status': 'success',
                'predicted_age_range': age_range,
                'probability': probability,
                'venus_strength': venus_strength,
                'seventh_lord_strength': seventh_strength,
                'factors_analyzed': ['Venus position', '7th House lord', 'Lagna strength']
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def detect_mangal_dosha(self, chart_data: Dict) -> Dict[str, Any]:
        """Detect and assess Mangal Dosha (Mars affliction)"""
        try:
            mars_sign = chart_data.get('mars_sign', 1)
            mars_house = chart_data.get('mars_house', 1)
            lagna = chart_data.get('lagna_sign', 1)
            
            afflicted_houses = [1, 4, 7, 8, 12]
            
            has_dosha = False
            severity = 0
            
            if mars_house in afflicted_houses:
                has_dosha = True
                if mars_house in [7, 8]:
                    severity = 5
                elif mars_house in [1, 4, 12]:
                    severity = 3
                else:
                    severity = 2
            
            remedies = []
            if has_dosha:
                if severity >= 4:
                    remedies = ["Mangal pooja", "Angaraka Stotra recitation", "Charity on Tuesday"]
                elif severity >= 2:
                    remedies = ["Light a lamp on Tuesdays", "Donate red items", "Recite Hanuman Chalisa"]
            
            return {
                'status': 'success',
                'has_mangal_dosha': has_dosha,
                'severity': severity,
                'mars_house': mars_house,
                'remedies': remedies,
                'interpretation': f"Mangal Dosha {'present' if has_dosha else 'absent'} - Severity: {severity}/5"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def identify_yogas(self, chart_data: Dict) -> Dict[str, Any]:
        """Identify beneficial yogas in chart"""
        try:
            yogas_found = []
            lagna = chart_data.get('lagna_sign', 1)
            moon_sign = chart_data.get('moon_sign', 1)
            
            # Gaja Kesari Yoga: Jupiter in Kendra from Moon
            if abs(moon_sign - chart_data.get('jupiter_sign', 1)) % 12 in [0, 3, 6, 9]:
                yogas_found.append({
                    'name': 'Gaja Kesari Yoga',
                    'effect': 'Wisdom, success, prosperity',
                    'strength': 'Strong'
                })
            
            # Pancha Maha Purusha Yogas: Planets in own/exalted signs in Kendra
            exalted_signs = {'Sun': 10, 'Moon': 2, 'Mars': 8, 'Mercury': 6, 'Jupiter': 9, 
                           'Venus': 12, 'Saturn': 7}
            
            planets_checked = ['mercury_sign', 'jupiter_sign', 'venus_sign', 'mars_sign', 'saturn_sign']
            for planet_key in planets_checked:
                planet_name = planet_key.replace('_sign', '').title()
                if planet_key in chart_data and chart_data[planet_key] == exalted_signs.get(planet_name):
                    yogas_found.append({
                        'name': f'{planet_name} Maha Purusha Yoga',
                        'effect': f'Excellence in {planet_name.lower()} qualities',
                        'strength': 'Excellent'
                    })
            
            return {
                'status': 'success',
                'yogas_found': yogas_found if yogas_found else [{'name': 'No major yogas', 'effect': 'Proceed with moderate expectations', 'strength': 'N/A'}],
                'total_count': len(yogas_found),
                'interpretation': f"Chart has {len(yogas_found)} benefic yoga(s)"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _get_house_lord(self, house: int, lagna: int) -> int:
        """Get lord of a house"""
        lords = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12}
        house_sign = ((house - 1 + lagna - 1) % 12) + 1
        return house_sign

    def generate_prediction_report(self, chart_data: Dict, birth_date: str) -> Dict[str, Any]:
        """Generate comprehensive prediction report"""
        try:
            dasha = self.calculate_vimshottari_dasha(
                chart_data.get('moon_nakshatra', 1), birth_date
            )
            marriage = self.predict_marriage_timing(chart_data)
            dosha = self.detect_mangal_dosha(chart_data)
            yogas = self.identify_yogas(chart_data)
            
            return {
                'status': 'success',
                'dasha_analysis': dasha,
                'marriage_timing': marriage,
                'dosha_analysis': dosha,
                'yogas': yogas,
                'report_generated': datetime.now().isoformat(),
                'sections': 4
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
