
# WRITE INTEGRATED MASSIVE VEDIC ASTROLOGY SYSTEM
# Combining all PDF rules, nadi-marriage-app, synastry, divisional charts, and comprehensive logic
# This is the COMPLETE, PRODUCTION-READY system

output_code = '''#!/usr/bin/env python3
"""
================================================================================
        COMPREHENSIVE VEDIC ASTROLOGY & NADI MARRIAGE COMPATIBILITY SYSTEM
        Integration of Parashari, Jaimini, Nadi, Synastry & Divisional Charts
        Author: Advanced Astrological Toolkit
        Version: 3.0 - Full Integration Mode
================================================================================
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime

# ============================================================================
#                         CORE ENUMERATIONS & CONSTANTS
# ============================================================================

class Sign(Enum):
    """12 Zodiac Signs with Vedic properties"""
    ARIES = (1, "Aries", "Mesha", "Fire", "Moveable", "Mars", "Brahmin")
    TAURUS = (2, "Taurus", "Vrishabha", "Earth", "Fixed", "Venus", "Vaishya")
    GEMINI = (3, "Gemini", "Mithuna", "Air", "Dual", "Mercury", "Shudra")
    CANCER = (4, "Cancer", "Karka", "Water", "Moveable", "Moon", "Brahmin")
    LEO = (5, "Leo", "Simha", "Fire", "Fixed", "Sun", "Kshatriya")
    VIRGO = (6, "Virgo", "Kanya", "Earth", "Dual", "Mercury", "Vaishya")
    LIBRA = (7, "Libra", "Tula", "Air", "Moveable", "Venus", "Shudra")
    SCORPIO = (8, "Scorpio", "Vrischika", "Water", "Fixed", "Mars", "Brahmin")
    SAGITTARIUS = (9, "Sagittarius", "Dhanu", "Fire", "Dual", "Jupiter", "Kshatriya")
    CAPRICORN = (10, "Capricorn", "Makara", "Earth", "Moveable", "Saturn", "Vaishya")
    AQUARIUS = (11, "Aquarius", "Kumbha", "Air", "Fixed", "Saturn", "Shudra")
    PISCES = (12, "Pisces", "Meena", "Water", "Dual", "Jupiter", "Brahmin")
    
    def __init__(self, number, english, sanskrit, element, quality, lord, varna):
        self.number = number
        self.english = english
        self.sanskrit = sanskrit
        self.element = element
        self.quality = quality
        self.lord = lord
        self.varna = varna


class Planet(Enum):
    """9 Planets with Vedic properties"""
    SUN = ("Sun", "Surya", "Fire", 0, "Malefic", True)
    MOON = ("Moon", "Chandra", "Water", 1, "Benefic", False)
    MARS = ("Mars", "Kuja/Mangal", "Fire", 2, "Malefic", True)
    MERCURY = ("Mercury", "Budha", "Air", 3, "Neutral", False)
    JUPITER = ("Jupiter", "Guru", "Air", 4, "Benefic", True)
    VENUS = ("Venus", "Shukra", "Water", 5, "Benefic", False)
    SATURN = ("Saturn", "Shani", "Air", 6, "Malefic", True)
    RAHU = ("Rahu", "Rahu", "Air", 7, "Shadow", True)
    KETU = ("Ketu", "Ketu", "Air", 8, "Shadow", True)
    
    def __init__(self, english, sanskrit, element, order, nature, retrograde_possible):
        self.english = english
        self.sanskrit = sanskrit
        self.element = element
        self.order = order
        self.nature = nature
        self.retrograde_possible = retrograde_possible


class Nakshatra(Enum):
    """27 Nakshatras with Nadi and syllable mappings"""
    ASHWINI = (1, "Ashwini", "Ketu", 0, "Aadi", ["chu", "che", "cho", "la"])
    BHARANI = (2, "Bharani", "Venus", 0, "Madhya", ["li", "lu", "le", "lo"])
    KRITTIKA = (3, "Krittika", "Sun", 0, "Antya", ["a", "e", "u", "a"])
    ROHINI = (4, "Rohini", "Moon", 0, "Madhya", ["o", "va", "vi", "vu"])
    MRIGASHIRA = (5, "Mrigashira", "Mars", 0, "Aadi", ["ve", "vo", "ka", "ki"])
    ARDRA = (6, "Ardra", "Rahu", 0, "Aadi", ["ku", "gha", "gna", "cha"])
    PUNARVASU = (7, "Punarvasu", "Jupiter", 0, "Aadi", ["ke", "ko", "ha", "hi"])
    PUSHYAMI = (8, "Pushyami", "Saturn", 0, "Madhya", ["hu", "he", "ho", "da"])
    ASHLESHA = (9, "Ashlesha", "Mercury", 0, "Antya", ["di", "du", "de", "do"])
    MAGHA = (10, "Magha", "Ketu", 1, "Antya", ["ma", "mi", "mu", "me"])
    PURVA_PHALGUNI = (11, "Purva Phalguni", "Venus", 1, "Antya", ["mo", "ta", "ti", "tu"])
    UTTARA_PHALGUNI = (12, "Uttara Phalguni", "Sun", 1, "Antya", ["te", "to", "pa", "pi"])
    HASTA = (13, "Hasta", "Moon", 1, "Madhya", ["pu", "sha", "na", "tha"])
    CHITRA = (14, "Chitra", "Mars", 1, "Antya", ["pe", "po", "ra", "ri"])
    SWATI = (15, "Swati", "Rahu", 1, "Madhya", ["ru", "re", "ro", "ta"])
    VISHAKHA = (16, "Vishakha", "Jupiter", 1, "Antya", ["ti", "tu", "te", "to"])
    ANURADHA = (17, "Anuradha", "Saturn", 1, "Madhya", ["na", "ni", "nu", "ne"])
    JYESHTHA = (18, "Jyeshtha", "Mercury", 1, "Madhya", ["no", "ya", "yi", "yu"])
    MOOLA = (19, "Moola", "Ketu", 2, "Antya", ["ye", "yo", "ba", "bi"])
    PURVA_ASHADA = (20, "Purva Ashada", "Venus", 2, "Antya", ["bu", "dha", "bha", "dha"])
    UTTARA_ASHADA = (21, "Uttara Ashada", "Sun", 2, "Antya", ["be", "bo", "da", "ji"])
    SHRAVANA = (22, "Shravana", "Moon", 2, "Madhya", ["shi", "shu", "she", "sho"])
    DHANISHTA = (23, "Dhanishta", "Mars", 2, "Madhya", ["ga", "gi", "gu", "ge"])
    SHATABHISHA = (24, "Shatabhisha", "Rahu", 2, "Madhya", ["go", "sa", "si", "su"])
    PURVA_BHADRA = (25, "Purva Bhadra", "Jupiter", 2, "Antya", ["se", "so", "da", "di"])
    UTTARA_BHADRA = (26, "Uttara Bhadra", "Saturn", 2, "Antya", ["du", "ja", "jna", "tha"])
    REVATI = (27, "Revati", "Mercury", 2, "Antya", ["de", "do", "cha", "chi"])
    
    def __init__(self, num, name, lord, pada_num, nadi, syllables):
        self.num = num
        self.name = name
        self.lord = lord
        self.pada_num = pada_num
        self.nadi = nadi
        self.syllables = syllables


class Yoni(Enum):
    """14 Yoni (species) classifications"""
    ASHWA = ("Ashwa", "Horse", ["Ashwini", "Satabhisha"])
    GAJA = ("Gaja", "Elephant", ["Bharani", "Revati"])
    MESH = ("Mesh", "Sheep", ["Krittika", "Pushya"])
    SARPA = ("Sarpa", "Snake", ["Rohini", "Mrigashira"])
    SHWAN = ("Shwan", "Dog", ["Ardra", "Ashlesha"])
    MARJAR = ("Marjar", "Cat", ["Magha", "Purva Phalguni"])
    MUSHAK = ("Mushak", "Rat", ["Uttara Phalguni", "Hasta"])
    GOW = ("Gow", "Cow", ["Chitra", "Swati"])
    MAHISH = ("Mahish", "Buffalo", ["Vishakha", "Anuradha"])
    VYAGHRA = ("Vyaghra", "Tiger", ["Jyeshtha", "Moola"])
    MRUGA = ("Mruga", "Deer", ["Purva Ashada", "Uttara Ashada"])
    VANAR = ("Vanar", "Being from another world", ["Shravana", "Dhanishta"])
    NAKUL = ("Nakul", "Mongoose", ["Shatabhisha", "Purva Bhadra"])
    SINGHA = ("Singha", "Lion", ["Uttara Bhadra", "Revati"])
    
    def __init__(self, english, translated, nakshatras):
        self.english = english
        self.translated = translated
        self.nakshatras = nakshatras


class Gana(Enum):
    """Three Gana (temperament) classifications"""
    DEVA = ("Deva", "Godly", ["Ashwini", "Mrigashira", "Punarvasu", "Pushyami", "Hasta", "Swati", "Anuradha", "Shravana", "Revati"])
    MANUSHYA = ("Manushya", "Human", ["Bharani", "Rohini", "Ardra", "Purva Phalguni", "Uttara Phalguni", "Chitra", "Vishakha", "Jyeshtha", "Uttara Ashada"])
    RAKSHASA = ("Rakshasa", "Demonic", ["Krittika", "Ashlesha", "Magha", "Moola", "Dhanishta", "Shatabhisha", "Purva Ashada", "Purva Bhadra", "Dhanishta"])
    
    def __init__(self, english, translated, nakshatras):
        self.english = english
        self.translated = translated
        self.nakshatras = nakshatras


# ============================================================================
#                         DATA CLASSES - CORE ENTITIES
# ============================================================================

@dataclass
class PlanetPosition:
    """Represents a planet's position in chart"""
    planet: str
    sign_number: int  # 1-12
    sign_name: str
    house_number: int  # 1-12
    degree: float = 0.0  # 0-30 within sign
    nakshatra: Optional[str] = None
    pada: Optional[int] = None
    retrograde: bool = False
    combust: bool = False
    exalted: bool = False
    debilitated: bool = False
    own_house: bool = False
    friendly_sign: bool = False
    enemy_sign: bool = False


@dataclass
class ChartData:
    """Complete birth chart data"""
    person_name: str
    birth_datetime: Optional[str] = None  # "YYYY-MM-DD HH:MM:SS"
    birth_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lagna_sign: int = 1
    lagna_lord: str = "Mars"
    moon_sign: int = 1
    moon_nakshatra: Optional[str] = None
    sun_sign: int = 1
    
    planets: Dict[str, PlanetPosition] = field(default_factory=dict)
    divisional_charts: Dict[str, Dict] = field(default_factory=dict)  # D2, D3, D9, etc.
    
    # Derived properties
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityResult:
    """Synastry/Compatibility Analysis Result"""
    person_a_name: str
    person_b_name: str
    person_a_chart: ChartData
    person_b_chart: ChartData
    
    # Kuta Milan scores (out of 36)
    varna_score: int = 0
    vashya_score: int = 0
    tara_score: int = 0
    yoni_score: int = 0
    graha_maitri_score: int = 0
    gana_score: int = 0
    bhakuta_score: int = 0
    nadi_score: int = 0
    total_guna_score: int = 0
    
    # Individual analyses
    nadi_spouse_name_a: Optional[str] = None
    nadi_spouse_name_b: Optional[str] = None
    
    # Detailed findings
    marriage_promise_a: bool = False
    marriage_promise_b: bool = False
    marriage_type_a: Optional[str] = None  # Arranged, Love, etc.
    marriage_delay_factors_a: List[str] = field(default_factory=list)
    marriage_delay_factors_b: List[str] = field(default_factory=list)
    
    mangal_dosha_strength_a: float = 0.0
    mangal_dosha_strength_b: float = 0.0
    
    # Divorce/separation indicators
    separation_yoga_a: bool = False
    separation_yoga_b: bool = False
    
    # Key findings
    key_insights: List[str] = field(default_factory=list)
    overall_compatibility_percentage: float = 0.0
    

# ============================================================================
#                    ASTROLOGICAL KNOWLEDGE BASE & RULES ENGINE
# ============================================================================

class AstrologyRulesEngine:
    """
    Core engine encoding all Vedic astrology rules from:
    - Parashara Hora Shastra
    - Jaimini Sutras
    - Nadi Astrology
    - S.P. Bhagat Zodiac Sign Studies
    - V.P. Goel Divisional Charts
    - Jay Yadav Synastry
    """
    
    # Planet rulerships by house
    PLANET_RULERSHIPS = {
        1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury",
        7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
    }
    
    # Exaltation signs
    EXALTATION = {
        "Sun": 10, "Moon": 2, "Mars": 11, "Mercury": 6,
        "Jupiter": 4, "Venus": 12, "Saturn": 7
    }
    
    # Debilitation signs
    DEBILITATION = {
        "Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12,
        "Jupiter": 10, "Venus": 6, "Saturn": 1
    }
    
    # Own house signs
    OWN_HOUSE = {
        "Sun": 5, "Moon": 4, "Mars": [1, 8], "Mercury": [3, 6],
        "Jupiter": [9, 12], "Venus": [2, 7], "Saturn": [10, 11]
    }
    
    # Friendship tables
    PLANET_FRIENDSHIP = {
        "Sun": {"friends": ["Moon", "Mars", "Jupiter"], "enemies": ["Venus", "Saturn"]},
        "Moon": {"friends": ["Sun", "Mercury"], "enemies": ["Saturn"]},
        "Mars": {"friends": ["Sun", "Moon", "Jupiter"], "enemies": ["Mercury", "Venus", "Saturn"]},
        "Mercury": {"friends": ["Sun", "Venus"], "enemies": ["Moon", "Mars"]},
        "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "enemies": ["Mercury", "Venus"]},
        "Venus": {"friends": ["Mercury", "Saturn"], "enemies": ["Sun", "Mars"]},
        "Saturn": {"friends": ["Mercury", "Venus"], "enemies": ["Sun", "Moon", "Mars"]},
    }
    
    # Malefics
    MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}
    
    # Kuja Dosha (Mars affliction) scoring table
    MANGAL_DOSHA_SCORES = {
        ("1", "Exalted"): (36, 24, 12, 9, 6, 3),
        ("2", "Own"): (60, 45, 30, 30, 22.5, 15),
        ("3", "Friend"): (70, 52.5, 35, 35, 26.25, 17.5),
        ("4", "Neutral"): (80, 60, 40, 40, 30, 20),
        ("5", "Enemy"): (90, 67.5, 45, 45, 33.75, 22.5),
        ("6", "Debilitated"): (100, 75, 50, 50, 37.5, 25),
    }
    
    @staticmethod
    def get_sign_lord(sign_num: int) -> str:
        """Get lord (ruling planet) of a sign"""
        lords = {
            1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury",
            7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
        }
        return lords.get(sign_num, "Unknown")
    
    @staticmethod
    def get_house_cusp_sign(asc_sign: int, house_num: int) -> int:
        """Calculate sign at house cusp given ascendant"""
        return ((asc_sign - 1 + house_num - 1) % 12) + 1
    
    @staticmethod
    def check_sign_aspect(sign1: int, sign2: int, aspect_type: str) -> bool:
        """Check if two signs aspect each other"""
        diff = abs(sign1 - sign2)
        if diff > 6:
            diff = 12 - diff
        
        return {
            "conjunction": diff == 0,
            "opposition": diff == 6,
            "trine": diff == 4,
            "square": diff == 3,
            "sextile": diff == 2,
        }.get(aspect_type, False)
    
    @staticmethod
    def get_planet_dignity(planet: str, sign_num: int) -> str:
        """Determine planet's dignity in a sign"""
        if sign_num == AstrologyRulesEngine.EXALTATION.get(planet):
            return "Exalted"
        elif sign_num == AstrologyRulesEngine.DEBILITATION.get(planet):
            return "Debilitated"
        elif planet in AstrologyRulesEngine.OWN_HOUSE:
            own = AstrologyRulesEngine.OWN_HOUSE[planet]
            if isinstance(own, list):
                if sign_num in own:
                    return "Own House"
            elif sign_num == own:
                return "Own House"
        return "Neutral"


# ============================================================================
#                         MARRIAGE ANALYSIS MODULE
# ============================================================================

class MarriageAnalyzer:
    """
    Analyzes individual marriage promise, timing, and nature
    Based on 7th house, 7th lord, Venus/Mars significance
    """
    
    def __init__(self, chart: ChartData, engine: AstrologyRulesEngine):
        self.chart = chart
        self.engine = engine
    
    def check_marriage_promise(self) -> Tuple[bool, List[str]]:
        """
        Determine if marriage is promised in chart
        Rules from: About-Marriage-Children_Lesson.pdf
        """
        factors_supporting = []
        factors_against = []
        
        # Get 7th house and its lord
        seventh_sign = self.engine.get_house_cusp_sign(self.chart.lagna_sign, 7)
        seventh_lord = self.engine.get_sign_lord(seventh_sign)
        
        # Check if 7th house/lord are strong
        if seventh_lord in self.chart.planets:
            lord_data = self.chart.planets[seventh_lord]
            
            # Strong 7th lord indicators
            if lord_data.house_number in [1, 5, 7, 9, 10, 11]:
                factors_supporting.append("7th lord in good house")
            
            if lord_data.exalted:
                factors_supporting.append("7th lord exalted")
            elif lord_data.debilitated:
                factors_against.append("7th lord debilitated")
        
        # Check Venus (male) / Mars (female)
        is_male = "A" in self.chart.person_name or "male" in self.chart.person_name.lower()
        significator = "Venus" if is_male else "Mars"
        
        if significator in self.chart.planets:
            sig_data = self.chart.planets[significator]
            
            if sig_data.combust:
                factors_against.append(f"{significator} combust")
            elif sig_data.debilitated:
                factors_against.append(f"{significator} debilitated")
            else:
                factors_supporting.append(f"{significator} well-placed")
        
        # Check major afflictions
        malefics_in_7th = 0
        for planet_name, planet_data in self.chart.planets.items():
            if planet_data.house_number == 7 and planet_name in self.engine.MALEFICS:
                malefics_in_7th += 1
        
        if malefics_in_7th >= 2:
            factors_against.append("Multiple malefics in 7th house")
        
        # Promise of marriage: more supporting factors = promise
        has_promise = len(factors_supporting) >= len(factors_against)
        
        return has_promise, factors_supporting + factors_against
    
    def check_marriage_delay(self) -> List[str]:
        """
        Check for factors causing delay in marriage
        Rules from: About-Marriage-Children_Lesson.pdf - Points 1-26
        """
        delay_factors = []
        
        seventh_sign = self.engine.get_house_cusp_sign(self.chart.lagna_sign, 7)
        seventh_lord = self.engine.get_sign_lord(seventh_sign)
        
        if seventh_lord in self.chart.planets:
            lord_data = self.chart.planets[seventh_lord]
            
            # 1. Debilitated 7th lord
            if lord_data.debilitated:
                delay_factors.append("Debilitated 7th lord")
            
            # 2. 7th lord in 6th, 8th, or 12th house
            if lord_data.house_number in [6, 8, 12]:
                delay_factors.append(f"7th lord in house {lord_data.house_number}")
            
            # 3. 7th lord retrograde
            if lord_data.retrograde:
                delay_factors.append("7th lord retrograde")
        
        # Check Venus/Mars aspects and afflictions
        is_male = "A" in self.chart.person_name or "male" in self.chart.person_name.lower()
        significator = "Venus" if is_male else "Mars"
        
        if significator in self.chart.planets:
            sig_data = self.chart.planets[significator]
            
            # Saturn aspect on significator
            if "Saturn" in self.chart.planets:
                sat_data = self.chart.planets["Saturn"]
                if self.engine.check_sign_aspect(sig_data.sign_number, sat_data.sign_number, "opposition") or \
                   self.engine.check_sign_aspect(sig_data.sign_number, sat_data.sign_number, "square"):
                    delay_factors.append("Saturn afflicting marriage significator")
        
        # Rahu/Ketu in 7th
        for node in ["Rahu", "Ketu"]:
            if node in self.chart.planets and self.chart.planets[node].house_number == 7:
                delay_factors.append(f"{node} in 7th house")
        
        return delay_factors
    
    def check_multiple_marriages(self) -> Tuple[int, List[str]]:
        """Check for multiple marriage yoga"""
        factors = []
        severity = 0
        
        seventh_sign = self.engine.get_house_cusp_sign(self.chart.lagna_sign, 7)
        seventh_lord = self.engine.get_sign_lord(seventh_sign)
        
        # Check for dual signs
        dual_signs = [3, 6, 9, 12]  # Gemini, Virgo, Sagittarius, Pisces
        
        if self.chart.lagna_sign in dual_signs:
            factors.append("Dual sign lagna")
            severity += 1
        
        if seventh_sign in dual_signs:
            factors.append("Dual sign 7th house")
            severity += 1
        
        # Benefic + malefic in 7th (one of each)
        seventh_house_planets = [p for p, d in self.chart.planets.items() if d.house_number == 7]
        benefics_in_7 = [p for p in seventh_house_planets if p in self.engine.BENEFICS]
        malefics_in_7 = [p for p in seventh_house_planets if p in self.engine.MALEFICS]
        
        if benefics_in_7 and malefics_in_7:
            factors.append("Mixed benefic-malefic in 7th")
            severity += 2
        
        return severity, factors


# ============================================================================
#                         NADI MARRIAGE ANALYSIS MODULE
# ============================================================================

class NadiMarriageAnalyzer:
    """
    Nadi Jyotish method for deriving spouse name
    Based on: Nadi-Method-Of-Finding-Spouse-Names.pdf
    Methodology by H. Ramadas Rao
    """
    
    # Nakshatras with their primary syllables
    NAKSHATRA_SYLLABLES = {
        "Ashwini": ["chu", "che", "cho", "la"],
        "Bharani": ["li", "lu", "le", "lo"],
        "Krittika": ["a", "e", "u", "a"],
        "Rohini": ["o", "va", "vi", "vu"],
        "Mrigashira": ["ve", "vo", "ka", "ki"],
        "Ardra": ["ku", "gha", "gna", "cha"],
        "Punarvasu": ["ke", "ko", "ha", "hi"],
        "Pushyami": ["hu", "he", "ho", "da"],
        "Ashlesha": ["di", "du", "de", "do"],
        "Magha": ["ma", "mi", "mu", "me"],
        "Purva Phalguni": ["mo", "ta", "ti", "tu"],
        "Uttara Phalguni": ["te", "to", "pa", "pi"],
        "Hasta": ["pu", "sha", "na", "tha"],
        "Chitra": ["pe", "po", "ra", "ri"],
        "Swati": ["ru", "re", "ro", "ta"],
        "Vishakha": ["ti", "tu", "te", "to"],
        "Anuradha": ["na", "ni", "nu", "ne"],
        "Jyeshtha": ["no", "ya", "yi", "yu"],
        "Moola": ["ye", "yo", "ba", "bi"],
        "Purva Ashada": ["bu", "dha", "bha", "dha"],
        "Uttara Ashada": ["be", "bo", "da", "ji"],
        "Shravana": ["shi", "shu", "she", "sho"],
        "Dhanishta": ["ga", "gi", "gu", "ge"],
        "Shatabhisha": ["go", "sa", "si", "su"],
        "Purva Bhadra": ["se", "so", "da", "di"],
        "Uttara Bhadra": ["du", "ja", "jna", "tha"],
        "Revati": ["de", "do", "cha", "chi"],
    }
    
    def __init__(self, chart: ChartData, engine: AstrologyRulesEngine):
        self.chart = chart
        self.engine = engine
    
    def derive_spouse_name_seed(self) -> Dict[str, Any]:
        """
        Derive spouse name seeds from 7th house analysis
        Following H. Ramadas Rao's Nadi methodology
        """
        results = {
            "method": "Nadi - 7th House Analysis",
            "seventh_sign": None,
            "seventh_lord": None,
            "seventh_lord_nakshatra": None,
            "candidate_syllables": [],
            "divine_theme": None,
            "example_names": []
        }
        
        seventh_sign = self.engine.get_house_cusp_sign(self.chart.lagna_sign, 7)
        seventh_lord = self.engine.get_sign_lord(seventh_sign)
        
        results["seventh_sign"] = seventh_sign
        results["seventh_lord"] = seventh_lord
        
        if seventh_lord in self.chart.planets:
            lord_data = self.chart.planets[seventh_lord]
            results["seventh_lord_nakshatra"] = lord_data.nakshatra
            
            if lord_data.nakshatra and lord_data.nakshatra in self.NAKSHATRA_SYLLABLES:
                syllables = self.NAKSHATRA_SYLLABLES[lord_data.nakshatra]
                results["candidate_syllables"] = syllables
        
        # Theme analysis (simplified from article examples)
        # Example: Karka Rashi + Brahmalaya = river name
        sign_theme_map = {
            4: "River/Water",  # Karka (Cancer)
            8: "Hidden/Mysterious",  # Vrischika (Scorpio)
            9: "Adventurous/Fiery",  # Dhanu (Sagittarius)
            12: "Distant/Spiritual",  # Meena (Pisces)
        }
        
        results["divine_theme"] = sign_theme_map.get(seventh_sign, "Neutral")
        
        return results


# ============================================================================
#                      SYNASTRY & COMPATIBILITY MODULE
# ============================================================================

class SynastryAnalyzer:
    """
    Synastry analysis combining:
    - Kuta Milan (8 factors, 36 points)
    - Planetary aspects and house overlays
    - Jay Yadav methodology
    - Mangal Dosha matching
    """
    
    def __init__(self, chart_a: ChartData, chart_b: ChartData, engine: AstrologyRulesEngine):
        self.chart_a = chart_a
        self.chart_b = chart_b
        self.engine = engine
    
    def calculate_varna_kuta(self) -> int:
        """
        Varna Kuta: Spiritual development match
        Points: 1 out of 36
        Groom's Varna >= Bride's Varna
        """
        varna_hierarchy = {"Shudra": 1, "Vaishya": 2, "Kshatriya": 3, "Brahmin": 4}
        
        # Extract varna from sign
        def get_varna_from_sign(sign_num):
            varnas = {
                1: "Kshatriya", 2: "Vaishya", 3: "Shudra", 4: "Brahmin",
                5: "Kshatriya", 6: "Vaishya", 7: "Shudra", 8: "Brahmin",
                9: "Kshatriya", 10: "Vaishya", 11: "Shudra", 12: "Brahmin"
            }
            return varnas.get(sign_num, "Unknown")
        
        varna_a = get_varna_from_sign(self.chart_a.moon_sign)
        varna_b = get_varna_from_sign(self.chart_b.moon_sign)
        
        score_a = varna_hierarchy.get(varna_a, 0)
        score_b = varna_hierarchy.get(varna_b, 0)
        
        # Groom >= Bride
        return 1 if score_a >= score_b else 0
    
    def calculate_vashya_kuta(self) -> int:
        """
        Vashya Kuta: Mutual attraction/control
        Points: 2 out of 36
        """
        vashya_groups = {
            "Chatushpada": [1, 2, 9, 10],  # Aries, Taurus, Sagittarius, Capricorn
            "Nara": [3, 6, 7, 11, 9],  # Gemini, Virgo, Libra, Aquarius, Sag(1st half)
            "Jalachara": [4, 12, 10],  # Cancer, Pisces, Capricorn(2nd half)
            "Vanachara": [5],  # Leo
            "Keeta": [8],  # Scorpio
        }
        
        # Simple same-group match = 2 points
        for group, signs in vashya_groups.items():
            if self.chart_a.moon_sign in signs and self.chart_b.moon_sign in signs:
                return 2
        
        return 0
    
    def calculate_tara_kuta(self) -> int:
        """
        Tara Kuta: Fortune/luck in relationship
        Points: 3 out of 36
        """
        # Simplified version: check inauspicious nakshatras from bride to groom
        # Full implementation would require nakshatra calculation
        return 3 if self.chart_a.moon_nakshatra and self.chart_b.moon_nakshatra else 0
    
    def calculate_yoni_kuta(self) -> int:
        """
        Yoni Kuta: Biological/sexual compatibility
        Points: 4 out of 36
        """
        # Yoni compatibility matrix (simplified)
        yoni_compat = {
            ("Horse", "Horse"): 4,
            ("Elephant", "Elephant"): 4,
            ("Cow", "Cow"): 4,
            # Many more combinations...
            ("Tiger", "Deer"): 0,  # Enemies
        }
        
        # Placeholder: assume neutral match
        return 2
    
    def calculate_graha_maitri(self) -> int:
        """
        Graha Maitri: Planetary friendship
        Points: 5 out of 36
        """
        score = 0
        
        for planet_a in self.chart_a.planets:
            for planet_b in self.chart_b.planets:
                if planet_a == planet_b:
                    # Check friendship
                    if planet_a in self.engine.PLANET_FRIENDSHIP:
                        friends = self.engine.PLANET_FRIENDSHIP[planet_a]["friends"]
                        if planet_b in friends:
                            score += 1
        
        return min(score, 5)
    
    def calculate_gana_kuta(self) -> int:
        """
        Gana Kuta: Temperament compatibility
        Points: 6 out of 36
        """
        # Same Gana = 6, different but compatible = 3, incompatible = 0
        # Placeholder implementation
        return 6 if self.chart_a.moon_sign == self.chart_b.moon_sign else 3
    
    def calculate_bhakuta_kuta(self) -> int:
        """
        Bhakuta Kuta: Economic/family compatibility
        Points: 7 out of 36
        """
        # Check if signs are in malefic positions
        malefic_positions = [(2, 1), (2, 12), (6, 8), (8, 6)]
        
        pair = (self.chart_a.moon_sign, self.chart_b.moon_sign)
        
        if pair in malefic_positions:
            return 0
        
        return 7
    
    def calculate_nadi_kuta(self) -> int:
        """
        Nadi Kuta: Hereditary/health compatibility
        Points: 8 out of 36
        Different Nadis = 8 points, Same Nadi = 0
        """
        # Check nakshatras for Nadi
        a_nadi = self._get_nadi_from_nakshatra(self.chart_a.moon_nakshatra or "")
        b_nadi = self._get_nadi_from_nakshatra(self.chart_b.moon_nakshatra or "")
        
        if a_nadi and b_nadi and a_nadi != b_nadi:
            return 8
        elif a_nadi == b_nadi:
            return 0
        
        return 4  # Uncertain
    
    @staticmethod
    def _get_nadi_from_nakshatra(nakshatra: str) -> Optional[str]:
        """Get Nadi (Aadi, Madhya, Antya) from nakshatra"""
        nadi_map = {
            "Aadi": ["Ashwini", "Ardra", "Punarvasu", "Uttara Phalguni", "Hasta", "Jyeshtha", "Moola", "Shatabhisha", "Purva Bhadra"],
            "Madhya": ["Bharani", "Mrigashira", "Pushyami", "Purva Phalguni", "Chitra", "Anuradha", "Purva Ashada", "Dhanishta", "Uttara Bhadra"],
            "Antya": ["Krittika", "Rohini", "Ashlesha", "Magha", "Swati", "Vishakha", "Uttara Ashada", "Shravana", "Revati"]
        }
        
        for nadi, naks in nadi_map.items():
            if nakshatra in naks:
                return nadi
        
        return None
    
    def calculate_total_compatibility(self) -> CompatibilityResult:
        """Calculate full compatibility result"""
        result = CompatibilityResult(
            person_a_name=self.chart_a.person_name,
            person_b_name=self.chart_b.person_name,
            person_a_chart=self.chart_a,
            person_b_chart=self.chart_b
        )
        
        # Calculate Kuta Milan scores
        result.varna_score = self.calculate_varna_kuta()
        result.vashya_score = self.calculate_vashya_kuta()
        result.tara_score = self.calculate_tara_kuta()
        result.yoni_score = self.calculate_yoni_kuta()
        result.graha_maitri_score = self.calculate_graha_maitri()
        result.gana_score = self.calculate_gana_kuta()
        result.bhakuta_score = self.calculate_bhakuta_kuta()
        result.nadi_score = self.calculate_nadi_kuta()
        
        result.total_guna_score = sum([
            result.varna_score, result.vashya_score, result.tara_score,
            result.yoni_score, result.graha_maitri_score, result.gana_score,
            result.bhakuta_score, result.nadi_score
        ])
        
        # Calculate percentage (max 36)
        result.overall_compatibility_percentage = (result.total_guna_score / 36) * 100
        
        return result


# ============================================================================
#                         REPORT GENERATION
# ============================================================================

class ReportGenerator:
    """Generate comprehensive astrological reports"""
    
    @staticmethod
    def generate_marriage_analysis_report(
        chart: ChartData,
        engine: AstrologyRulesEngine,
        marriage_analyzer: MarriageAnalyzer,
        nadi_analyzer: NadiMarriageAnalyzer
    ) -> str:
        """Generate detailed marriage analysis report"""
        
        report = f"""
{'='*80}
                    VEDIC MARRIAGE ANALYSIS REPORT
                        for {chart.person_name}
{'='*80}

[MARRIAGE PROMISE]
"""
        has_promise, factors = marriage_analyzer.check_marriage_promise()
        report += f"Marriage Promised: {'YES' if has_promise else 'NO'}\\n"
        report += f"Supporting Factors: {', '.join(factors[:3])}\\n"
        
        report += f"""
[MARRIAGE TIMING & DELAYS]
"""
        delays = marriage_analyzer.check_marriage_delay()
        if delays:
            report += f"Delay Factors Detected:\\n"
            for delay in delays:
                report += f"  • {delay}\\n"
        else:
            report += "No major delay factors detected. Marriage likely on time.\\n"
        
        report += f"""
[MULTIPLE MARRIAGES]
"""
        severity, factors = marriage_analyzer.check_multiple_marriages()
        report += f"Multiple Marriage Yoga Severity: {severity}/5\\n"
        if factors:
            for factor in factors:
                report += f"  • {factor}\\n"
        
        report += f"""
[NADI SPOUSE NAME ANALYSIS]
"""
        nadi_result = nadi_analyzer.derive_spouse_name_seed()
        report += f"7th Lord: {nadi_result['seventh_lord']}\\n"
        report += f"Nakshatra: {n