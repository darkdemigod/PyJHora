
def format_chart_info(chart_info):
    """
    Format chart information by removing empty strings and cleaning up formatting
    
    Args:
        chart_info: List of chart information strings
    
    Returns:
        Formatted string with chart information
    """
    formatted_info = ""
    for item in chart_info:
        if item:  # Check if the item is not an empty string
            formatted_info += f"{item.strip()}\n"
    return formatted_info.strip()

def format_astrology_data(data):
    """
    Format astrological data dictionary into readable text
    
    Args:
        data: Dictionary with astrological data (keys and values)
    
    Returns:
        Formatted string with key-value pairs
    """
    if not data:
        return "No data available"
    
    formatted_data = "\n".join([f"{key}: {value}" for key, value in data.items()])
    return formatted_data

def format_horoscope_output(horoscope_info, chart_info, calendar_info=None):
    """
    Format complete horoscope output including calendar info, chart data, and positions
    
    Args:
        horoscope_info: Dictionary with planetary positions and calculations
        chart_info: List with chart layout information  
        calendar_info: Optional dictionary with calendar/panchanga information
    
    Returns:
        Formatted string with complete horoscope information
    """
    output = []
    
    # Add calendar information if provided
    if calendar_info:
        output.append("=== CALENDAR INFORMATION ===")
        output.append(format_astrology_data(calendar_info))
        output.append("")
    
    # Add chart layout
    if chart_info:
        output.append("=== CHART LAYOUT ===")
        output.append(format_chart_info(chart_info))
        output.append("")
    
    # Add horoscope calculations
    if horoscope_info:
        output.append("=== PLANETARY POSITIONS & CALCULATIONS ===")
        output.append(format_astrology_data(horoscope_info))
    
    return "\n".join(output)

def clean_astrological_symbols(text):
    """
    Clean up astrological symbols and formatting for better readability
    
    Args:
        text: String containing astrological symbols
    
    Returns:
        Cleaned text with readable format
    """
    # Replace common astrological symbols with readable text
    symbol_replacements = {
        '♈': 'Aries',
        '♉': 'Taurus', 
        '♊': 'Gemini',
        '♋': 'Cancer',
        '♌': 'Leo',
        '♍': 'Virgo',
        '♎': 'Libra',
        '♏': 'Scorpio', 
        '♐': 'Sagittarius',
        '♑': 'Capricorn',
        '♒': 'Aquarius',
        '♓': 'Pisces',
        '☉': 'Sun',
        '☾': 'Moon',
        '♂': 'Mars',
        '☿': 'Mercury', 
        '♃': 'Jupiter',
        '♀': 'Venus',
        '♄': 'Saturn',
        '☊': 'Rahu',
        '☋': 'Ketu',
        'ℒ': 'Lagna'
    }
    
    cleaned_text = text
    for symbol, replacement in symbol_replacements.items():
        cleaned_text = cleaned_text.replace(symbol, replacement)
    
    return cleaned_text
