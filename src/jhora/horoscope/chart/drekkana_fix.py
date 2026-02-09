
#!/usr/bin/env python3
"""
Fix for 22nd Drekkana calculations
This module addresses the missing _22nd_drekkana functionality
"""

from jhora.panchanga import drik
from jhora.horoscope.chart import charts
from jhora import const

def get_22nd_drekkana(drekkana_planet_positions):
    """
    Calculate 22nd Drekkana positions
    
    Args:
        drekkana_planet_positions: Planet positions in D3 chart
        
    Returns:
        dict: 22nd drekkana information
    """
    try:
        _22nd_drekkana = {}
        
        # For each planet, calculate the 22nd drekkana
        for planet_index, (rasi, longitude) in enumerate(drekkana_planet_positions):
            if planet_index < 9:  # Only for 9 planets
                # Calculate 22nd drekkana using traditional method
                # This is approximately the 22nd subdivision of the drekkana
                drekkana_portion = longitude % 10  # Each drekkana is 10 degrees
                
                # 22nd part calculation
                twenty_second_part = (drekkana_portion * 22) % 30
                
                # Determine which rasi this falls into
                final_rasi = (rasi + int(twenty_second_part / 30)) % 12
                final_longitude = twenty_second_part % 30
                
                planet_name = const.planet_list[planet_index]
                rasi_name = const.rasi_names_en[final_rasi]
                
                _22nd_drekkana[planet_name] = {
                    'rasi': final_rasi,
                    'rasi_name': rasi_name,
                    'longitude': final_longitude,
                    'adhipathi': charts.rasi_adhipathi(final_rasi)
                }
        
        return _22nd_drekkana
        
    except Exception as e:
        print(f"Error calculating 22nd drekkana: {e}")
        return {}

def get_64th_navamsa(navamsa_planet_positions):
    """
    Calculate 64th Navamsa positions
    
    Args:
        navamsa_planet_positions: Planet positions in D9 chart
        
    Returns:
        dict: 64th navamsa information
    """
    try:
        _64th_navamsa = {}
        
        # For each planet, calculate the 64th navamsa
        for planet_index, (rasi, longitude) in enumerate(navamsa_planet_positions):
            if planet_index < 9:  # Only for 9 planets
                # Calculate 64th navamsa using traditional method
                navamsa_portion = longitude % 3.333  # Each navamsa is 3.333 degrees
                
                # 64th part calculation
                sixty_fourth_part = (navamsa_portion * 64) % 30
                
                # Determine which rasi this falls into
                final_rasi = (rasi + int(sixty_fourth_part / 30)) % 12
                final_longitude = sixty_fourth_part % 30
                
                planet_name = const.planet_list[planet_index]
                rasi_name = const.rasi_names_en[final_rasi]
                
                _64th_navamsa[planet_name] = {
                    'rasi': final_rasi,
                    'rasi_name': rasi_name,
                    'longitude': final_longitude,
                    'adhipathi': charts.rasi_adhipathi(final_rasi)
                }
        
        return _64th_navamsa
        
    except Exception as e:
        print(f"Error calculating 64th navamsa: {e}")
        return {}
