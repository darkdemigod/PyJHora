#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════
           VEDIC ASTROLOGY SYSTEM V4.0 - COMPREHENSIVE EXAMPLES
════════════════════════════════════════════════════════════════════════════════

This file contains 15+ complete working examples demonstrating the full
capabilities of the V4.0 system.

Run this file to see the system in action:
    $ python vedic_astrology_examples_v4.py

════════════════════════════════════════════════════════════════════════════════
"""

from vedic_astrology_main_v4 import initialize_system


def example_1_system_initialization():
    """
    Example 1: Initialize the system
    """
    print(f"""
    {"="*75}
    EXAMPLE 1: SYSTEM INITIALIZATION
    {"="*75}
    """)

    system = initialize_system()
    status = system.get_system_status()

    print(f"Version: {status['version']}")
    print(f"Status: {status['status']}")
    print(f"Ready for Analysis: {status['ready_for_analysis']}")


def example_2_load_knowledge_bases():
    """
    Example 2: Load all knowledge bases
    """
    print(f"""
    {"="*75}
    EXAMPLE 2: LOAD KNOWLEDGE BASES
    {"="*75}
    """)

    system = initialize_system()

    kb_files = {
        'predictive': 'Jyotish_Predictive-astrology_M.N.Kedar-rules-2.json',
        'nakshatras_vol1': 'Jyotish_Vashisht-Vaid_The-Secrets-of-Cosmic-Energy-Portals-_Nakshatras_vol-1-rules.json',
        'nakshatras_vol2': 'Jyotish_Vashisht-Vaid_The-Secrets-of-Cosmic-Energy-Portals-_Nakshatras_vol-2-rules.json',
        'prasna_marga': 'Prasna-Marga-Pt.-I_-Chs.-I-to-XVI-Eng.-Tr.-With-Original-Text-in-Devanagri-Notes-Pt.-1-PDFDrive-rules.json',
        'sacred_nadi': 'Jyotish_Vasantha-Sai_Sacred-Nadi-Readings-rules.json',
        'sukha_nadi': 'Jyotish_Sukha-nadi_part-2-rules.json',
        'rectification_1': 'Jyotish_1959_The-Nadi-rectification-tables_B.S.-RAO-rules.json',
        'rectification_2': 'Jyotish_1959_The-Nadi-rectification-tables_B.S.-RAO-fragments.json',
        'nadi_analysis': 'example-of-Nadi-analysis_Umang-Taneja-rules.json',
        'prashna_manual': 'prasna-manual_Divya-compilation-rules.json'
    }

    system.register_kb_files(kb_files)
    result = system.load_knowledge_bases()

    print(f"Files Loaded: {result['files_loaded']}")
    print(f"Total Rules: {result['total_rules']:,}")
    print(f"System Ready: {result['system_ready']}")


def example_3_add_birth_chart():
    """
    Example 3: Add a birth chart
    """
    print(f"""
    {"="*75}
    EXAMPLE 3: ADD BIRTH CHART
    {"="*75}
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Rajesh Kumar',
        'birth_datetime': '1985-03-15T09:30:00',
        'birth_location': 'Mumbai, India',
        'lagna_sign': 3,  # Gemini
        'moon_sign': 5,   # Leo
        'sun_sign': 12,   # Pisces
        'moon_nakshatra': 'Magha',
        'moon_nakshatra_lord': 'Sun',
        'planet_positions': {
            'Sun': {'sign': 12, 'degree': 0},
            'Moon': {'sign': 5, 'degree': 15},
            'Mars': {'sign': 8, 'degree': 23},
            'Mercury': {'sign': 1, 'degree': 10},
            'Jupiter': {'sign': 7, 'degree': 8},
            'Venus': {'sign': 2, 'degree': 12},
            'Saturn': {'sign': 9, 'degree': 20},
            'Rahu': {'sign': 6, 'degree': 15},
            'Ketu': {'sign': 12, 'degree': 15}
        }
    }

    result = system.add_chart('rajesh_1985', chart_data)
    print(f"Chart Added: {result['status']}")
    print(f"Person: {result['person']}")
    print(f"Total Charts: {result['total_charts']}")


def example_4_complete_chart_analysis():
    """
    Example 4: Complete chart delineation
    """
    print(f"""
    {"="*75}
    EXAMPLE 4: COMPLETE CHART DELINEATION
    {"="*75}

    This performs comprehensive analysis using ALL methods:
    - All 12 houses
    - All 9 planets
    - Divisional charts (D1-D30+)
    - Yogas & Doshas
    - Dasha periods
    - Current transits
    - Predictions
    - Personality assessment
    - Life area analysis (Career, Relationships, Health, Finance, Spiritual)
    - Personalized remedies
    """)

    system = initialize_system()

    # Add sample chart
    chart_data = {
        'person_name': 'Priya Sharma',
        'birth_datetime': '1990-07-22T15:45:00',
        'birth_location': 'Delhi, India',
        'lagna_sign': 1,
        'moon_sign': 9,
        'sun_sign': 4
    }

    system.add_chart('priya_1990', chart_data)

    # Perform analysis
    analysis = system.analyze_complete('priya_1990')

    print(f"Chart: {analysis['person']}")
    print(f"Analysis Date: {analysis['analysis_date']}")
    print(f"Sections: {list(analysis['sections'].keys())}")
    print(f"Methodology: {analysis['methodology']}")
    print(f"Confidence: {analysis['confidence']}")


def example_5_answer_when_will_i_marry():
    """
    Example 5: Answer "When will I marry?"
    """
    print(f"""
    {"="*75}
    EXAMPLE 5: ANSWER QUESTION - "WHEN WILL I MARRY?"
    {"="*75}
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Amit Patel',
        'birth_datetime': '1992-06-10T10:15:00',
        'birth_location': 'Ahmedabad, India',
        'lagna_sign': 7,  # Libra
        'moon_sign': 2,   # Taurus
        'sun_sign': 3     # Gemini
    }

    system.add_chart('amit_1992', chart_data)

    answer = system.answer_question('amit_1992', 'When will I marry?')

    print(f"Question: {answer['question']}")
    print(f"Question Type: {answer['question_type']}")
    print(f"Confidence: {answer['confidence']}")
    print(f"Answer: {answer['analysis']}")


def example_6_career_potential():
    """
    Example 6: Assess career potential
    """
    print(f"""
    {"="*75}
    EXAMPLE 6: CAREER POTENTIAL ASSESSMENT
    {"="*75}

    Analyzes:
    - 10th house & lord
    - Saturn (career indicator)
    - Sun (authority)
    - Mercury (communication)
    - Skills identification
    - Career timing
    - Recommended careers
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Vikram Singh',
        'birth_datetime': '1988-11-20T14:30:00',
        'birth_location': 'Bangalore, India',
        'lagna_sign': 10,
        'moon_sign': 11,
        'sun_sign': 8
    }

    system.add_chart('vikram_1988', chart_data)

    answer = system.answer_question('vikram_1988', 'What is my career potential?')

    print(f"Person: {answer['person']}")
    print(f"Analysis: {answer['analysis']}")


def example_7_compatibility_analysis():
    """
    Example 7: Marriage compatibility analysis (Kuta Milan)
    """
    print(f"""
    {"="*75}
    EXAMPLE 7: MARRIAGE COMPATIBILITY ANALYSIS
    {"="*75}

    Analyzes 8 Kuta Milan factors:
    1. Varna Kuta (1 point)
    2. Vashya Kuta (2 points)
    3. Tara Kuta (3 points)
    4. Yoni Kuta (4 points)
    5. Graha Maitri (5 points)
    6. Gana Kuta (6 points)
    7. Bhakuta Kuta (7 points)
    8. Nadi Kuta (8 points)

    Total: 36 points
    Excellent: 28-36
    Good: 20-27
    Fair: 12-19
    Poor: <12
    """)

    system = initialize_system()

    # Person 1
    chart1 = {
        'person_name': 'Arjun Verma',
        'birth_datetime': '1990-04-12T12:00:00',
        'birth_location': 'Jaipur, India',
        'lagna_sign': 1,
        'moon_sign': 5,
        'sun_sign': 1
    }

    # Person 2
    chart2 = {
        'person_name': 'Anjali Sharma',
        'birth_datetime': '1992-08-25T16:45:00',
        'birth_location': 'Lucknow, India',
        'lagna_sign': 7,
        'moon_sign': 11,
        'sun_sign': 5
    }

    system.add_chart('arjun_1990', chart1)
    system.add_chart('anjali_1992', chart2)

    compatibility = system.compatibility_analysis('arjun_1990', 'anjali_1992')

    print(f"Person 1: {compatibility['person1']}")
    print(f"Person 2: {compatibility['person2']}")
    print(f"Kuta Milan: {compatibility['kuta_milan']}")
    print(f"Analysis Date: {compatibility['analysis_date']}")


def example_8_mangal_dosha_assessment():
    """
    Example 8: Mangal Dosha (Mars Affliction) assessment
    """
    print(f"""
    {"="*75}
    EXAMPLE 8: MANGAL DOSHA ASSESSMENT
    {"="*75}

    Analyzes:
    - Mars position in 12 houses
    - Mars afflictions
    - Dosha strength levels
    - Remedies
    - Exceptions to Mangal Dosha
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Neha Kapoor',
        'birth_datetime': '1993-02-14T11:20:00',
        'birth_location': 'Pune, India',
        'lagna_sign': 4,
        'moon_sign': 8,
        'sun_sign': 11
    }

    system.add_chart('neha_1993', chart_data)

    answer = system.answer_question('neha_1993', 'Do I have Mangal Dosha?')

    print(f"Person: {answer['person']}")
    print(f"Confidence: {answer['confidence']}")
    print(f"Answer: {answer['analysis']}")


def example_9_predict_marriage_timing():
    """
    Example 9: Predict marriage timing
    """
    print(f"""
    {"="*75}
    EXAMPLE 9: MARRIAGE TIMING PREDICTION
    {"="*75}

    Uses:
    - Current Dasha analysis
    - 7th house & lord
    - Transits on 7th lord
    - Gochara analysis
    - Nakshatra periods
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Suresh Desai',
        'birth_datetime': '1989-09-18T13:40:00',
        'birth_location': 'Nagpur, India',
        'lagna_sign': 2,
        'moon_sign': 7,
        'sun_sign': 6
    }

    system.add_chart('suresh_1989', chart_data)

    prediction = system.predict_event('suresh_1989', 'marriage')

    print(f"Event: {prediction['event']}")
    print(f"Current Dasha: {prediction['current_dasha']}")
    print(f"Likelihood: {prediction['likelihood']}")
    print(f"Timeframe: {prediction['event_timing']}")


def example_10_health_indicators():
    """
    Example 10: Health analysis and disease indicators
    """
    print(f"""
    {"="*75}
    EXAMPLE 10: HEALTH INDICATORS ANALYSIS
    {"="*75}

    Analyzes:
    - 6th house (diseases)
    - 8th house (longevity)
    - Moon (physical health)
    - Mars (surgeries, accidents)
    - Saturn (chronic issues)
    - Timing of health issues
    - Preventive measures
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Ramesh Gupta',
        'birth_datetime': '1980-01-05T09:50:00',
        'birth_location': 'Chennai, India',
        'lagna_sign': 5,
        'moon_sign': 3,
        'sun_sign': 10
    }

    system.add_chart('ramesh_1980', chart_data)

    answer = system.answer_question('ramesh_1980', 'What about my health?')

    print(f"Person: {answer['person']}")
    print(f"Analysis Type: Health")
    print(f"Confidence: {answer['confidence']}")


def example_11_financial_outlook():
    """
    Example 11: Financial outlook and wealth
    """
    print(f"""
    {"="*75}
    EXAMPLE 11: FINANCIAL OUTLOOK
    {"="*75}

    Analyzes:
    - 2nd house (wealth)
    - 11th house (gains)
    - Jupiter (wealth indicator)
    - Hora chart (D2)
    - Wealth yoga
    - Loss periods
    - Business potential
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Isha Malhotra',
        'birth_datetime': '1991-05-30T15:15:00',
        'birth_location': 'Noida, India',
        'lagna_sign': 9,
        'moon_sign': 12,
        'sun_sign': 2
    }

    system.add_chart('isha_1991', chart_data)

    answer = system.answer_question('isha_1991', 'What is my financial potential?')

    print(f"Person: {answer['person']}")
    print(f"Financial Analysis: Available")
    print(f"Confidence: {answer['confidence']}")


def example_12_children_and_progeny():
    """
    Example 12: Children and progeny analysis
    """
    print(f"""
    {"="*75}
    EXAMPLE 12: CHILDREN & PROGENY ANALYSIS
    {"="*75}

    Analyzes:
    - 5th house (children)
    - 5th lord strength
    - Saptamsha chart (D7)
    - Jupiter influence
    - Timing of births
    - Children doshas
    - Remedies for childlessness
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Deepak Joshi',
        'birth_datetime': '1985-08-12T10:30:00',
        'birth_location': 'Surat, India',
        'lagna_sign': 6,
        'moon_sign': 1,
        'sun_sign': 5
    }

    system.add_chart('deepak_1985', chart_data)

    answer = system.answer_question('deepak_1985', 'Will I have children? When?')

    print(f"Person: {answer['person']}")
    print(f"Progeny Analysis: Available")


def example_13_spiritual_potential():
    """
    Example 13: Spiritual path and potential
    """
    print(f"""
    {"="*75}
    EXAMPLE 13: SPIRITUAL POTENTIAL
    {"="*75}

    Analyzes:
    - 9th house (Dharma)
    - 9th lord
    - Jupiter influence
    - Ketu influence
    - Moksha yoga
    - Spiritual breakthroughs
    - Meditation suitability
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Ananya Iyer',
        'birth_datetime': '1987-12-21T08:45:00',
        'birth_location': 'Bangalore, India',
        'lagna_sign': 11,
        'moon_sign': 9,
        'sun_sign': 9
    }

    system.add_chart('ananya_1987', chart_data)

    answer = system.answer_question('ananya_1987', 'What is my spiritual potential?')

    print(f"Person: {answer['person']}")
    print(f"Spiritual Analysis: Available")


def example_14_business_and_success():
    """
    Example 14: Business success and entrepreneurship
    """
    print(f"""
    {"="*75}
    EXAMPLE 14: BUSINESS SUCCESS ANALYSIS
    {"="*75}

    Analyzes:
    - 10th house (business)
    - 11th house (gains)
    - Mercury (commerce)
    - Venus (business partnerships)
    - 3rd house (ventures)
    - Timing for business launch
    - Success yoga
    - Losses periods
    """)

    system = initialize_system()

    chart_data = {
        'person_name': 'Rohan Khanna',
        'birth_datetime': '1986-03-25T12:30:00',
        'birth_location': 'Mumbai, India',
        'lagna_sign': 8,
        'moon_sign': 4,
        'sun_sign': 12
    }

    system.add_chart('rohan_1986', chart_data)

    prediction = system.predict_event('rohan_1986', 'business')

    print(f"Event: {prediction['event']}")
    print(f"Likelihood: {prediction['likelihood']}")
    print(f"Timing: {prediction['event_timing']}")


def example_15_system_statistics():
    """
    Example 15: System statistics and status
    """
    print(f"""
    {"="*75}
    EXAMPLE 15: SYSTEM STATISTICS & STATUS
    {"="*75}
    """)

    system = initialize_system()
    status = system.get_system_status()

    print(f"Version: {status['version']}")
    print(f"Status: {status['status']}")
    print(f"Charts Loaded: {status['charts_loaded']}")
    print(f"KB Files: {status['kb_files_registered']}")
    print(f"Analyses Performed: {status['analyses_performed']}")
    print(f"Ready: {status['ready_for_analysis']}")


# ════════════════════════════════════════════════════════════════════════════════
#                              RUN ALL EXAMPLES
# ════════════════════════════════════════════════════════════════════════════════

def run_all_examples():
    """Run all 15 examples."""

    examples = [
        ("System Initialization", example_1_system_initialization),
        ("Load Knowledge Bases", example_2_load_knowledge_bases),
        ("Add Birth Chart", example_3_add_birth_chart),
        ("Complete Chart Analysis", example_4_complete_chart_analysis),
        ("Marriage Timing", example_5_answer_when_will_i_marry),
        ("Career Potential", example_6_career_potential),
        ("Compatibility Analysis", example_7_compatibility_analysis),
        ("Mangal Dosha", example_8_mangal_dosha_assessment),
        ("Marriage Prediction", example_9_predict_marriage_timing),
        ("Health Indicators", example_10_health_indicators),
        ("Financial Outlook", example_11_financial_outlook),
        ("Children Analysis", example_12_children_and_progeny),
        ("Spiritual Potential", example_13_spiritual_potential),
        ("Business Success", example_14_business_and_success),
        ("System Statistics", example_15_system_statistics),
    ]

    print(f"""
    {'='*75}
    VEDIC ASTROLOGY SYSTEM V4.0 - COMPREHENSIVE EXAMPLES
    {'='*75}

    Running {len(examples)} examples demonstrating all capabilities...
    """)

    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
        except Exception as e:
            print(f"Example {i} ({name}): Error - {e}")

        print()


if __name__ == "__main__":
    run_all_examples()
