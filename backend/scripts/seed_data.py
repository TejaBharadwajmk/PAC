"""
PAC — Karnataka Crime Dataset Seed Script

Generates 1,500 realistic synthetic crime records for Karnataka State Police.

Design Principles:
  1. Behavioural Pattern Clusters — same MO expressed in different words
     so the Sentence Transformer similarity engine can detect them.
  2. Criminal Networks — repeat offenders linked across multiple crimes.
  3. Geographic Clustering — crimes cluster around known high-crime coordinates.
  4. Temporal Realism — 3-year history (2022-2024) with natural frequency patterns.

Usage (inside Docker):
  docker exec -it pac_backend python scripts/seed_data.py
  
Usage (local, with DB accessible on localhost:5432):
  DB_HOST=localhost python backend/scripts/seed_data.py
"""

import os
import sys
import uuid
import random
import json
import math
from datetime import datetime, timedelta, date

import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor

# ── DB Connection ──────────────────────────────────────────
DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME",     "pac_db"),
    "user":     os.getenv("DB_USER",     "pac_user"),
    "password": os.getenv("DB_PASSWORD", "pac_password"),
    "host":     os.getenv("DB_HOST",     "postgres"),
    "port":     int(os.getenv("DB_PORT", "5432")),
}

random.seed(42)  # Deterministic for reproducibility

# ═══════════════════════════════════════════════════════════
# DISTRICT DATA — Karnataka with coordinates + police stations
# ═══════════════════════════════════════════════════════════

DISTRICTS = {
    "Bengaluru Urban": {
        "code": "BLR-URB",
        "center": (12.9716, 77.5946),
        "radius_km": 0.08,
        "stations": [
            "Shivajinagar", "Cubbon Park", "Upparpet", "Cottonpet",
            "Whitefield", "Electronic City", "Yeshwantpur", "Rajajinagar",
            "Basavanagudi", "Jayanagar", "BTM Layout", "Indiranagar",
            "Koramangala", "Marathahalli", "Hebbal", "Kengeri",
        ],
        "crime_weight": 0.30,  # 30% of all crimes
    },
    "Mysuru": {
        "code": "MYS",
        "center": (12.2958, 76.6394),
        "radius_km": 0.04,
        "stations": [
            "Lakshmipuram", "Jayalakshmipuram", "Kuvempunagar",
            "Saraswathipuram", "Chamaraja", "Vijayanagar", "Hebbal",
        ],
        "crime_weight": 0.12,
    },
    "Dakshina Kannada": {
        "code": "DK",
        "center": (12.8703, 74.8421),
        "radius_km": 0.04,
        "stations": [
            "Mangaluru East", "Mangaluru North", "Mangaluru South",
            "Bunder", "Urwa", "Pandeshwara", "Kadri",
        ],
        "crime_weight": 0.10,
    },
    "Hubballi-Dharwad": {
        "code": "HBL",
        "center": (15.3647, 75.1240),
        "radius_km": 0.04,
        "stations": [
            "Hubballi Rural", "Hubballi City", "Dharwad",
            "Keshwapur", "Gokul Road", "Vidyanagar",
        ],
        "crime_weight": 0.09,
    },
    "Belagavi": {
        "code": "BLG",
        "center": (15.8497, 74.4977),
        "radius_km": 0.03,
        "stations": [
            "Belagavi City", "Khanapur", "Bailhongal", "Saundatti",
        ],
        "crime_weight": 0.08,
    },
    "Tumakuru": {
        "code": "TMK",
        "center": (13.3409, 77.1010),
        "radius_km": 0.03,
        "stations": [
            "Tumakuru Rural", "Tumakuru City", "Tiptur", "Sira",
        ],
        "crime_weight": 0.07,
    },
    "Shivamogga": {
        "code": "SMG",
        "center": (13.9299, 75.5681),
        "radius_km": 0.03,
        "stations": [
            "Shivamogga Rural", "Shivamogga City", "Sagar", "Bhadravathi",
        ],
        "crime_weight": 0.07,
    },
    "Kalaburagi": {
        "code": "KLB",
        "center": (17.3297, 76.8197),
        "radius_km": 0.03,
        "stations": [
            "Kalaburagi Rural", "Kalaburagi City", "Jewargi", "Aland",
        ],
        "crime_weight": 0.07,
    },
    "Bengaluru Rural": {
        "code": "BLR-RUR",
        "center": (13.2100, 77.5000),
        "radius_km": 0.05,
        "stations": ["Magadi", "Kanakapura", "Ramanagara", "Channapatna"],
        "crime_weight": 0.05,
    },
    "Raichur": {
        "code": "RCH",
        "center": (16.2120, 77.3439),
        "radius_km": 0.03,
        "stations": ["Raichur Rural", "Raichur City", "Manvi", "Devadurga"],
        "crime_weight": 0.05,
    },
}

# ═══════════════════════════════════════════════════════════
# CRIMINAL PROFILES — 30 criminals in 5 gangs + solo
# ═══════════════════════════════════════════════════════════

GANGS = [
    {
        "name": "Bike Bandit Gang",
        "specialty": "chain_snatching",
        "members": [
            {"name": "Rajesh Kumar Naik", "aliases": ["Rocky", "Bike Raj"], "age": 28, "district": "Bengaluru Urban", "is_repeat": True, "is_wanted": True},
            {"name": "Suresh Gowda",      "aliases": ["Suri"],             "age": 25, "district": "Bengaluru Urban", "is_repeat": True, "is_wanted": False},
            {"name": "Venkatesh B",       "aliases": ["Venki"],            "age": 30, "district": "Mysuru",          "is_repeat": True, "is_wanted": True},
            {"name": "Mahesh Reddy",      "aliases": ["Mahi", "Black Mahi"], "age": 27, "district": "Bengaluru Urban", "is_repeat": True, "is_wanted": False},
        ],
    },
    {
        "name": "Night Crawlers",
        "specialty": "house_break_in",
        "members": [
            {"name": "Ramesh Naik",       "aliases": ["Crow", "Iron Ram"],  "age": 35, "district": "Dakshina Kannada", "is_repeat": True,  "is_wanted": True},
            {"name": "Girish Shetty",     "aliases": ["Giri"],              "age": 32, "district": "Dakshina Kannada", "is_repeat": True,  "is_wanted": False},
            {"name": "Praveen Bangera",   "aliases": ["Pravi"],             "age": 29, "district": "Dakshina Kannada", "is_repeat": False, "is_wanted": False},
        ],
    },
    {
        "name": "Tech Fraud Gang",
        "specialty": "cyber_crime",
        "members": [
            {"name": "Sanjay Kumar Rao",  "aliases": ["Cyber Sanjay", "Boss"], "age": 33, "district": "Bengaluru Urban", "is_repeat": True,  "is_wanted": True},
            {"name": "Vijay Krishnappa",  "aliases": ["VK"],                   "age": 28, "district": "Bengaluru Urban", "is_repeat": True,  "is_wanted": False},
            {"name": "Anand Murthy",      "aliases": ["Andy"],                  "age": 26, "district": "Mysuru",          "is_repeat": False, "is_wanted": False},
        ],
    },
    {
        "name": "Highway Dacoits",
        "specialty": "dacoity",
        "members": [
            {"name": "Basavaraj Hosamani","aliases": ["Basu", "Tiger Basu"],  "age": 40, "district": "Belagavi",  "is_repeat": True,  "is_wanted": True},
            {"name": "Nagesh Patil",      "aliases": ["Nagu"],                 "age": 38, "district": "Belagavi",  "is_repeat": True,  "is_wanted": True},
            {"name": "Shankar Doddamani", "aliases": ["Shanku"],               "age": 35, "district": "Hubballi-Dharwad", "is_repeat": True, "is_wanted": False},
            {"name": "Raju Kamble",       "aliases": ["Raju Bhai"],            "age": 32, "district": "Belagavi",  "is_repeat": True,  "is_wanted": False},
            {"name": "Sunil Shinde",      "aliases": ["Sunil D"],              "age": 30, "district": "Belagavi",  "is_repeat": False, "is_wanted": False},
        ],
    },
    {
        "name": "Key Masters",
        "specialty": "vehicle_theft",
        "members": [
            {"name": "Kiran Devadiga",    "aliases": ["Key Kiran"],           "age": 31, "district": "Dakshina Kannada", "is_repeat": True,  "is_wanted": True},
            {"name": "Lokesh Hegde",      "aliases": ["Loki"],                "age": 27, "district": "Dakshina Kannada", "is_repeat": True,  "is_wanted": False},
        ],
    },
]

# Solo criminals (not in any gang)
SOLO_CRIMINALS = [
    {"name": "Prakash Chinnaswamy", "aliases": ["Chinna"], "age": 45, "district": "Bengaluru Urban", "is_repeat": True,  "is_wanted": False, "specialty": "theft"},
    {"name": "Harish Nair",         "aliases": ["Harry"],  "age": 24, "district": "Mysuru",          "is_repeat": False, "is_wanted": False, "specialty": "assault"},
    {"name": "Nagaraj Swamy",       "aliases": ["Naga"],   "age": 38, "district": "Kalaburagi",      "is_repeat": True,  "is_wanted": False, "specialty": "drug_offense"},
    {"name": "Umesh Poojary",       "aliases": ["Uma"],    "age": 29, "district": "Dakshina Kannada","is_repeat": False, "is_wanted": False, "specialty": "robbery"},
    {"name": "Dinesh Rao",          "aliases": ["Dinu"],   "age": 33, "district": "Shivamogga",      "is_repeat": True,  "is_wanted": False, "specialty": "fraud"},
    {"name": "Madhu Gowda",         "aliases": ["Madhu"],  "age": 22, "district": "Tumakuru",        "is_repeat": False, "is_wanted": False, "specialty": "theft"},
    {"name": "Santosh Nayak",       "aliases": ["Santo"],  "age": 36, "district": "Hubballi-Dharwad","is_repeat": True,  "is_wanted": False, "specialty": "burglary"},
    {"name": "Ganesh Kumar",        "aliases": ["Gani"],   "age": 41, "district": "Raichur",         "is_repeat": True,  "is_wanted": False, "specialty": "extortion"},
    {"name": "Shivakumar Prasad",   "aliases": ["Shiva"],  "age": 26, "district": "Bengaluru Rural", "is_repeat": False, "is_wanted": False, "specialty": "vehicle_theft"},
    {"name": "Manjunath Reddy",     "aliases": ["Manju"],  "age": 44, "district": "Bengaluru Urban", "is_repeat": True,  "is_wanted": True,  "specialty": "murder"},
]

# ═══════════════════════════════════════════════════════════
# MO TEXT TEMPLATES — Variations for each crime pattern
# Same behaviour, different words → tests similarity engine
# ═══════════════════════════════════════════════════════════

MO_TEMPLATES = {
    "chain_snatching": [
        "Two accused persons came on a motorcycle and snatched gold chain from {victim} near {location} and fled at high speed towards {direction}",
        "Suspects riding two-wheeler approached {victim} from behind and grabbed gold necklace before escaping at high speed",
        "Two unknown persons on a bike committed chain snatching from {victim} near {landmark} during {time_desc}",
        "Accused on two-wheeler snatched gold chain from {victim} who was walking near {landmark} and escaped towards {direction}",
        "Two persons came on motorcycle and forcibly snatched gold necklace valued at Rs.{value} from {victim} near {landmark}",
        "Chain snatching committed by two-wheeler borne accused from woman near {location}. Both accused wore helmets and fled towards {direction}",
        "Unknown accused on bike grabbed gold chain from victim near {location} and sped away before anyone could react",
        "Two suspects on motorcycle targeted {victim} near bus stand and snatched gold chain before fleeing at high speed",
        "Accused observed victim wearing gold chain at {location} and on motorcycle snatched chain and escaped",
        "Gang of two came on motorcycle and snatched gold chain from lady near {location}, fled towards {direction}",
        "Two accused persons approached victim on two wheeler and one pillion rider forcibly pulled gold chain and both fled",
        "Motorbike borne accused snatched gold ornament from pedestrian near {landmark} during {time_desc} and absconded",
        "Two miscreants on bike committed chain snatching near {location}. Victim raised alarm but accused had already fled",
        "Suspects on Royal Enfield motorcycle targeted woman wearing gold jewellery near {location} and snatched chain",
        "Chain snatching incident reported near {landmark}. Two accused on two-wheeler grabbed chain from victim and escaped towards {direction}",
    ],
    "house_break_in": [
        "Accused broke rear window glass using iron rod and entered house at midnight and committed theft of {stolen}",
        "Unknown persons forced entry through back door during night hours and stolen valuables including {stolen}",
        "Suspects entered through backside window at night by cutting window grill and stolen {stolen}",
        "Accused broke into house by removing window grill and stolen gold jewellery and cash worth Rs.{value}",
        "Two accused entered house from rear side by breaking window glass at midnight using crowbar",
        "Unknown persons entered through bathroom window at night and stolen {stolen} from almirah",
        "Accused cut window grill on backside and entered house in early morning hours and stolen valuables",
        "House break-in committed during night. Entry through rear window using iron rod. Stolen {stolen}",
        "Accused entered through back door by damaging padlock and committed theft of {stolen} in late night hours",
        "Two accused entered house through rear window using duplicate key and stolen {stolen} during night",
        "Suspects broke door latch on backside and entered house at 2am. Stolen gold ornaments and cash",
        "House burglary committed at midnight. Accused broke rear window glass using stone and stolen {stolen}",
        "Entry through backside compound wall. Accused cut window grill and entered house during late night hours",
        "Accused removed window grill on rear side and entered sleeping family's house and stolen {stolen}",
        "Night burglary. Two accused entered through back door after breaking lock. Stolen gold and silver ornaments",
    ],
    "atm_fraud": [
        "Accused installed card skimming device on ATM machine at {location} and cloned customer debit cards",
        "Suspects tampered with ATM machine to capture card information. Multiple customer accounts compromised",
        "Card skimmer device found installed in ATM near {location}. Accused cloned debit cards and withdrew cash",
        "ATM card data stolen using skimming device attached to ATM machine. Accused captured PIN using hidden camera",
        "Accused installed keypad overlay and card reader device on ATM at {location} to steal card credentials",
        "ATM skimming fraud committed. Unknown persons installed device on ATM machine and cloned {num} customer cards",
        "Skimming device attached to ATM at {location}. Customer card data stolen and used for unauthorized transactions",
        "Accused tampered with ATM card slot by installing skimmer device. Card data cloned and used for withdrawals",
        "ATM fraud detected at {location}. Device found which copied card data. Amount Rs.{value} fraudulently withdrawn",
        "Organized fraud using ATM skimming. Accused installed hardware device and hidden camera to steal card details",
    ],
    "cyber_fraud_otp": [
        "Accused called victim posing as bank official and obtained OTP. Amount Rs.{value} fraudulently debited from account",
        "Victim received call from unknown person posing as customer care. Shared OTP and Rs.{value} was debited",
        "Accused impersonated bank officer via phone call and obtained card details and OTP. Amount Rs.{value} transferred",
        "Vishing fraud. Accused called victim claiming bank account KYC update needed. Obtained OTP and debited Rs.{value}",
        "Unknown caller posing as bank representative asked victim to share OTP for account verification. Rs.{value} deducted",
        "Accused called victim saying account blocked. Obtained debit card number and OTP. Rs.{value} transferred fraudulently",
        "Telephone fraud. Accused posed as RBI official and obtained banking credentials from victim. Rs.{value} debited",
        "Victim deceived by fake bank call. OTP shared believing account update required. Rs.{value} fraud committed",
        "Social engineering fraud via phone. Accused obtained mobile banking credentials and transferred Rs.{value}",
        "Accused called victim from spoofed bank number. Convinced to share OTP for fake reward redemption. Rs.{value} lost",
        "Fake KYC call fraud. Accused claimed account would be blocked unless OTP shared. Rs.{value} debited immediately",
        "UPI fraud via fake phone call. Accused obtained UPI PIN from victim and debited Rs.{value} from account",
    ],
    "vehicle_theft": [
        "Accused stole motorcycle parked near {location} using duplicate key during {time_desc}",
        "Two-wheeler stolen from parking lot near {location}. Accused broke steering lock and took vehicle",
        "Motorcycle stolen by using duplicate key method. Vehicle found abandoned near {location}",
        "Bike theft from apartment parking. Accused cut lock and pushed vehicle before starting using two-wire method",
        "Accused stole two-wheeler from parking area using master key. Vehicle recovered near {location}",
        "Vehicle theft committed at night. Accused broke steering lock and started bike by bypassing ignition",
        "Motorcycle stolen from market parking. Accused used hotwire technique to start vehicle and fled",
        "Car stolen from residential area using sophisticated key cloning equipment during late night hours",
        "Two-wheeler theft from temple premises during {time_desc}. Accused used duplicate key to steal vehicle",
        "Motorcycle stolen while owner was in shop. Accused used two-wire method to bypass ignition and fled",
        "Bike theft committed near {landmark}. Accused broke steering lock and jumped vehicle to parking exit",
        "Vehicle stolen from public parking. Duplicate key used. Bike found abandoned 10 km away near {location}",
    ],
    "dacoity": [
        "Gang of {num} armed persons entered house and tied family members and committed dacoity. Stolen {stolen} at gunpoint",
        "Armed gang of {num} persons conducted organised dacoity on business premises. Stolen cash and valuables worth Rs.{value}",
        "Organised dacoity committed by gang of {num}. Accused armed with knives threatened owners and stole {stolen}",
        "Dacoity at residence. Gang of {num} entered at night, tied inmates and stole {stolen} and cash worth Rs.{value}",
        "Armed robbery committed by {num} person gang on gold shop. Accused displayed firearms and fled with {stolen}",
        "Dacoity on transport vehicle. Gang of {num} armed persons intercepted vehicle and robbed {stolen}",
        "Gang robbery at commercial establishment. {num} accused entered armed and threatened staff before taking {stolen}",
        "Organised gang of {num} with weapons raided gold shop during closing hours and committed dacoity",
        "Dacoity at factory. Gang of {num} overpowered security and stole {stolen} and cash at knifepoint",
        "Highway dacoity. Armed gang of {num} stopped vehicle and robbed occupants of {stolen} and cash",
    ],
    "robbery": [
        "Accused threatened victim at knife point near {location} and robbed gold chain and mobile phone",
        "Two accused approached {victim} and at knife point robbed gold jewellery and cash near {landmark}",
        "Accused threatened victim with iron rod and snatched purse containing cash near {location}",
        "Group of three persons blocked victim's path and at knife point demanded and robbed cash and valuables",
        "Accused used threatening behaviour and robbed mobile phone and cash from victim near {location}",
        "Victim threatened with knife and gold chain and cash robbed near {landmark} during {time_desc}",
        "Accused accosted victim near {location} and with weapon threatened to harm and robbed valuables",
        "Robbery committed by accused who threatened victim with bottle and robbed mobile and cash",
    ],
    "drug_offense": [
        "Accused found in possession of {drug} weighing {weight} grams near {location}",
        "Drug peddler arrested near {location} with {drug} valued at Rs.{value}",
        "Accused arrested while transporting {drug} in vehicle near {location}. Substance worth Rs.{value} seized",
        "Drug supply chain busted. Accused arrested with {drug} weighing {weight} grams from residence",
        "Person found distributing {drug} near {location} arrested. {weight} grams recovered",
        "Accused caught red-handed peddling {drug} near {location}. Total quantity {weight} grams",
        "Organized drug racket busted. Accused arrested with {drug} worth Rs.{value} at {location}",
    ],
    "assault": [
        "Accused attacked victim with iron rod following dispute over property near {location}",
        "Group of accused attacked victim near {landmark} following altercation over old enmity",
        "Accused assaulted victim with knife following personal dispute. Victim sustained injuries",
        "Gang attacked victim near {location} following financial dispute. Multiple accused involved",
        "Victim assaulted by accused with wooden log following argument over money",
        "Accused attacked victim with weapon near {landmark} in premeditated attack",
        "Physical assault by group following dispute at {location}. Victim hospitalized",
    ],
    "theft": [
        "Accused stole mobile phone and cash from victim while in crowd at {location}",
        "Pickpocket incident near {location}. Victim lost purse with cash Rs.{value}",
        "Accused stole valuable items from vehicle parked at {location} by breaking window",
        "Theft of mobile phone from victim at bus stop near {landmark}",
        "Accused stole two-wheeler parts from vehicle parked at {location}",
        "Shop theft. Accused stole {stolen} from unattended shop during daytime",
        "Items stolen from victim's home by unknown person during their absence",
    ],
    "burglary": [
        "Accused broke into commercial establishment at night by cutting shutter and stolen cash from cash box",
        "Unknown persons broke into shop after closing hours by removing lock and stolen goods worth Rs.{value}",
        "Shop break-in during night. Accused broke front glass door and stolen {stolen} from premises",
        "Commercial establishment targeted at night. Accused cut padlock and stolen cash and electronic goods",
        "Accused broke shutter lock of medical shop and stolen medicines and cash worth Rs.{value}",
        "Shop burglary. Accused removed rolling shutter lock and stolen {stolen} worth Rs.{value}",
    ],
    "murder": [
        "Accused committed murder of victim using knife following dispute over property at {location}",
        "Body found near {location}. Investigation revealed murder by accused using sharp weapon over financial dispute",
        "Victim attacked with sharp weapon following old enmity. Succumbed to injuries",
        "Murder committed using blunt weapon following dispute over woman. Accused fled after crime",
        "Accused stabbed victim multiple times following property dispute. Victim died on the way to hospital",
    ],
    "fraud": [
        "Accused cheated victim on pretext of selling property and received Rs.{value} advance without delivering",
        "Investment fraud. Accused promised high returns on investment and collected Rs.{value} before absconding",
        "Job fraud. Accused collected money from multiple victims promising government job. Rs.{value} cheated",
        "Accused collected advance payment of Rs.{value} for construction work but failed to complete project",
        "Online shopping fraud. Victim paid Rs.{value} for product on fake website. Product never delivered",
    ],
}

# Helper lists for template filling
LOCATIONS = [
    "market area", "bus stand", "railway station", "main road", "residential area",
    "temple premises", "ATM corner", "shopping complex", "signal junction",
    "park road", "vegetable market", "hospital road", "school area", "lake road",
]
LANDMARKS = [
    "near KSRTC bus stand", "near main market", "near town hall", "near temple",
    "near school gate", "near petrol bunk", "near hospital", "near railway crossing",
    "near flyover", "near shopping mall",
]
DIRECTIONS = ["north", "south", "east", "west", "towards city", "towards highway", "unknown direction"]
TIMES = ["morning hours", "evening hours", "night hours", "late night hours", "afternoon hours"]
STOLEN_ITEMS = [
    "gold ornaments and cash", "gold chain, bangles and cash",
    "mobile phone and cash", "gold jewellery", "cash and documents",
    "laptop and mobile", "silver articles and cash", "electronic goods",
]
DRUGS = ["ganja", "heroin", "cannabis", "MDMA", "methamphetamine", "smack"]
VICTIM_NAMES = [
    "Savitha", "Lakshmi", "Rekha", "Meena", "Usha", "Anitha", "Vidya",
    "Kavitha", "Radha", "Sujatha", "Vijaya", "Nalini", "Padma", "Geeta",
    "Ramesh", "Suresh", "Venkat", "Prakash", "Kumar", "Mohan", "Ravi",
]

# ═══════════════════════════════════════════════════════════
# SEEDING LOGIC
# ═══════════════════════════════════════════════════════════

def random_coords(center_lat: float, center_lon: float, radius_deg: float):
    """Random point near a center within radius_deg degrees."""
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius_deg)
    return (
        center_lat + r * math.sin(angle),
        center_lon + r * math.cos(angle),
    )


def fill_template(template: str, crime_type: str) -> str:
    """Fill MO template variables with random realistic values."""
    return template.format(
        victim=random.choice(VICTIM_NAMES),
        location=random.choice(LOCATIONS),
        landmark=random.choice(LANDMARKS),
        direction=random.choice(DIRECTIONS),
        time_desc=random.choice(TIMES),
        value=random.choice([5000, 10000, 15000, 25000, 50000, 75000, 100000, 150000, 200000]),
        stolen=random.choice(STOLEN_ITEMS),
        num=random.randint(3, 8),
        weight=round(random.uniform(5, 500), 1),
        drug=random.choice(DRUGS),
        num_victims=random.randint(5, 50),
    )


def get_crime_mo_features(crime_type: str, mo_text: str) -> dict:
    """Simple rule-based feature extraction matching the backend service."""
    text = mo_text.lower()

    # Crime method
    crime_method = "confrontation"
    if any(kw in text for kw in ["broke", "forced", "smashed", "cut grill"]):
        crime_method = "forced_entry"
    elif any(kw in text for kw in ["otp", "online", "phishing", "skimm", "posing"]):
        crime_method = "cyber"
    elif any(kw in text for kw in ["deceived", "impersonated", "posed"]):
        crime_method = "deception"
    elif any(kw in text for kw in ["snatched", "grabbed", "robbed"]):
        crime_method = "confrontation"

    # Time of day
    time_of_day = "unknown"
    if any(kw in text for kw in ["midnight", "late night", "2am", "3am", "4am"]):
        time_of_day = "late_night"
    elif any(kw in text for kw in ["night", "10pm", "11pm"]):
        time_of_day = "night"
    elif any(kw in text for kw in ["evening", "5pm", "6pm", "7pm"]):
        time_of_day = "evening"
    elif any(kw in text for kw in ["morning", "6am", "7am", "8am"]):
        time_of_day = "morning"

    # Target type
    target_type = "individual"
    if any(kw in text for kw in ["house", "home", "residence", "flat"]):
        target_type = "residence"
    elif any(kw in text for kw in ["shop", "store", "establishment"]):
        target_type = "shop"
    elif any(kw in text for kw in ["atm", "card machine"]):
        target_type = "atm"
    elif any(kw in text for kw in ["vehicle", "motorcycle", "car", "parked bike"]):
        target_type = "vehicle"

    # Gang
    gang_involved = any(kw in text for kw in ["gang", "group", "two accused", "three", "four", "five", "six"])
    num_accused = 1
    if "two" in text or "2 accused" in text:
        num_accused = 2
    elif "three" in text or "3" in text:
        num_accused = 3
    elif "four" in text or "4" in text:
        num_accused = 4
    elif any(str(n) in text for n in range(5, 10)):
        num_accused = random.randint(5, 8)
    elif gang_involved:
        num_accused = 2

    # Escape
    escape_method = "unknown"
    if any(kw in text for kw in ["bike", "motorcycle", "two-wheeler", "motorbike", "scooter"]):
        escape_method = "bike"
    elif any(kw in text for kw in ["car", "vehicle", "auto"]):
        escape_method = "car"
    elif "foot" in text:
        escape_method = "foot"

    vehicle_used = escape_method in ("bike", "car")

    # Tags
    tags = []
    if vehicle_used:
        tags.append("vehicle_used")
    if time_of_day in ("night", "late_night"):
        tags.append("night_operation")
    if gang_involved:
        tags.append("gang_crime")
    if target_type == "residence":
        tags.append("residential")
    if any(kw in text for kw in ["gold", "chain", "jewellery", "necklace"]):
        tags.append("gold_theft")
    if escape_method == "bike":
        tags.append("two_wheeler")
    if crime_type in ("cyber_crime", "atm_fraud", "fraud"):
        tags.append("financial_fraud")

    # Planning
    planning_level = "opportunistic"
    if any(kw in text for kw in ["pre-planned", "surveyed", "systematically", "planned in advance"]):
        planning_level = "highly_planned"
    elif any(kw in text for kw in ["duplicate key", "skimmer", "followed", "waited"]):
        planning_level = "planned"
    elif crime_type in ("cyber_crime", "atm_fraud", "fraud", "dacoity", "kidnapping"):
        planning_level = "planned"

    return {
        "crime_method": crime_method,
        "entry_method": "direct" if crime_type == "chain_snatching" else (
            "rear_window" if "rear window" in text or "back window" in text else (
                "online" if crime_type in ("cyber_crime", "atm_fraud") else "unknown"
            )
        ),
        "target_type": target_type,
        "weapon_used": (
            "knife" if "knife" in text else
            "gun" if "gun" in text or "firearm" in text else
            "iron_rod" if "iron rod" in text or "crowbar" in text else "none"
        ),
        "tools_used": (
            ["crowbar"] if "crowbar" in text else
            ["duplicate_key"] if "duplicate key" in text else
            ["skimmer"] if "skimmer" in text else []
        ),
        "time_of_day": time_of_day,
        "day_type": "unknown",
        "planning_level": planning_level,
        "gang_involved": gang_involved,
        "num_accused": num_accused,
        "escape_method": escape_method,
        "vehicle_used_in_crime": vehicle_used,
        "modus_operandi_tags": tags,
    }


# Crime type distribution (total = 1500 crimes)
CRIME_DISTRIBUTION = [
    ("chain_snatching",  300, "chain_snatching"),
    ("house_break_in",   250, "house_break_in"),
    ("cyber_fraud_otp",  180, "cyber_crime"),
    ("atm_fraud",        120, "atm_fraud"),
    ("vehicle_theft",    150, "vehicle_theft"),
    ("robbery",          120, "robbery"),
    ("dacoity",           80, "dacoity"),
    ("drug_offense",      80, "drug_offense"),
    ("assault",           80, "assault"),
    ("theft",             60, "theft"),
    ("burglary",          50, "burglary"),
    ("fraud",             30, "fraud"),
    ("murder",            20, "murder"),
]

TOTAL_CRIMES = sum(c[1] for c in CRIME_DISTRIBUTION)
print(f"Total crimes to seed: {TOTAL_CRIMES}")

# Crime severity mapping
SEVERITY_MAP = {
    "murder": "critical",
    "dacoity": "critical",
    "chain_snatching": "medium",
    "house_break_in": "medium",
    "robbery": "high",
    "atm_fraud": "high",
    "cyber_fraud_otp": "medium",
    "vehicle_theft": "low",
    "drug_offense": "medium",
    "assault": "high",
    "theft": "low",
    "burglary": "medium",
    "fraud": "medium",
}

# ── Date range ─────────────────────────────────────────────
START_DATE = datetime(2022, 1, 1)
END_DATE   = datetime(2024, 12, 31)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days


def random_occurred_at() -> datetime:
    days = random.randint(0, DATE_RANGE_DAYS)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    return START_DATE + timedelta(days=days, hours=hours, minutes=minutes)


def pick_district() -> tuple:
    districts = list(DISTRICTS.keys())
    weights = [DISTRICTS[d]["crime_weight"] for d in districts]
    return random.choices(districts, weights=weights, k=1)[0], districts


def pick_district_weighted() -> str:
    districts = list(DISTRICTS.keys())
    weights = [DISTRICTS[d]["crime_weight"] for d in districts]
    return random.choices(districts, weights=weights, k=1)[0]


# ═══════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ═══════════════════════════════════════════════════════════

def seed(conn):
    cur = conn.cursor()

    print("\n[1/6] Creating admin and officer users...")
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    users_data = [
        # Admin
        (str(uuid.uuid4()), "ADMIN001", "System Administrator", "admin@ksp.gov.in",
         "Bengaluru Urban", "Headquarters", "admin", pwd_ctx.hash("Admin@2024")),
        # Supervisors
        (str(uuid.uuid4()), "SUP001", "DCP Suresh Kumar", "sup001@ksp.gov.in",
         "Bengaluru Urban", "Shivajinagar", "supervisor", pwd_ctx.hash("Sup@2024")),
        (str(uuid.uuid4()), "SUP002", "DCP Rekha Naik", "sup002@ksp.gov.in",
         "Mysuru", "Lakshmipuram", "supervisor", pwd_ctx.hash("Sup@2024")),
        # Analysts
        (str(uuid.uuid4()), "ANA001", "SI Priya Rao", "ana001@ksp.gov.in",
         "Bengaluru Urban", "Shivajinagar", "analyst", pwd_ctx.hash("Ana@2024")),
        # Officers
        (str(uuid.uuid4()), "OFF001", "HC Ravi Kumar", "off001@ksp.gov.in",
         "Bengaluru Urban", "Whitefield", "officer", pwd_ctx.hash("Off@2024")),
        (str(uuid.uuid4()), "OFF002", "HC Mahesh Gowda", "off002@ksp.gov.in",
         "Mysuru", "Kuvempunagar", "officer", pwd_ctx.hash("Off@2024")),
        (str(uuid.uuid4()), "OFF003", "HC Lakshmi Patil", "off003@ksp.gov.in",
         "Dakshina Kannada", "Mangaluru East", "officer", pwd_ctx.hash("Off@2024")),
    ]
    execute_batch(cur, """
        INSERT INTO users (id, badge_number, full_name, email, district, police_station, role, hashed_password)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (badge_number) DO NOTHING
    """, users_data)
    conn.commit()
    print(f"  Created {len(users_data)} users. Admin badge: ADMIN001 / Admin@2024")

    # Get admin user ID for registering crimes
    cur.execute("SELECT id FROM users WHERE badge_number = 'ADMIN001'")
    admin_id = str(cur.fetchone()[0])

    # ── Create Criminals ────────────────────────────────────
    print("\n[2/6] Creating criminal profiles...")
    criminal_ids = {}  # name → uuid

    all_criminals = []
    for gang in GANGS:
        for m in gang["members"]:
            all_criminals.append({**m, "gang_name": gang["name"], "gang_affiliation": True})
    for c in SOLO_CRIMINALS:
        all_criminals.append({**c, "gang_name": None, "gang_affiliation": False})

    criminal_rows = []
    for c in all_criminals:
        cid = str(uuid.uuid4())
        criminal_ids[c["name"]] = cid
        age = c.get("age", random.randint(20, 50))
        criminal_rows.append((
            cid,
            c["name"],
            json.dumps(c.get("aliases", [])),
            None,  # dob
            age,
            "male",
            c.get("district", "Bengaluru Urban"),
            "Karnataka",
            f"Address in {c.get('district', 'Bengaluru Urban')}",
            None,  # contact
            c.get("is_repeat", False),
            random.randint(2, 15) if c.get("is_repeat") else random.randint(0, 2),
            c.get("gang_name"),
            c.get("gang_affiliation", False),
            random.randint(160, 185),
            random.choice(["slim", "medium", "heavy"]),
            None,
            c.get("is_wanted", False),
            False,
        ))

    execute_batch(cur, """
        INSERT INTO criminals (
            id, name, aliases, date_of_birth, age, gender, district, state, address,
            contact_number, is_repeat_offender, previous_cases_count, gang_name,
            gang_affiliation, height_cm, build, identifying_marks, is_wanted, is_arrested
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, criminal_rows)
    conn.commit()
    print(f"  Created {len(criminal_rows)} criminals")

    # Build gang → criminal IDs lookup
    gang_criminals = {}
    for gang in GANGS:
        gang_criminals[gang["name"]] = [criminal_ids[m["name"]] for m in gang["members"]]

    # ── FIR counter per district per year ──────────────────
    fir_counters = {}

    def next_fir(district: str, year: int) -> str:
        key = f"{district}_{year}"
        fir_counters[key] = fir_counters.get(key, 0) + 1
        code = DISTRICTS[district]["code"]
        return f"FIR/{code}/{year}/{fir_counters[key]:04d}"

    # ── Create crimes ───────────────────────────────────────
    print("\n[3/6] Creating crimes with MO text (this takes a moment)...")

    all_crime_ids = []  # (crime_id, crime_type_key)

    crime_rows = []
    crime_mo_rows = []

    for (mo_key, count, crime_type_val) in CRIME_DISTRIBUTION:
        templates = MO_TEMPLATES[mo_key]

        for _ in range(count):
            district = pick_district_weighted()
            dist_data = DISTRICTS[district]
            center_lat, center_lon = dist_data["center"]
            lat, lon = random_coords(center_lat, center_lon, dist_data["radius_km"])
            station = random.choice(dist_data["stations"])
            occurred = random_occurred_at()
            year = occurred.year
            fir = next_fir(district, year)

            # Pick a random MO template and fill it
            template = random.choice(templates)
            try:
                mo_text = fill_template(template, crime_type_val)
            except (KeyError, IndexError):
                mo_text = template  # fallback

            crime_id = str(uuid.uuid4())
            severity = SEVERITY_MAP.get(mo_key, "medium")

            crime_rows.append((
                crime_id, fir, crime_type_val, severity, "registered",
                district, station,
                f"Near {random.choice(LOCATIONS)}, {district}",
                round(lat, 6), round(lon, 6),
                f"SRID=4326;POINT({round(lon, 6)} {round(lat, 6)})",
                f"Crime incident of type {crime_type_val.replace('_', ' ')} in {district}",
                mo_text,
                occurred, occurred + timedelta(hours=random.randint(1, 12)),
                admin_id,
            ))

            # MO features
            mo_feats = get_crime_mo_features(mo_key, mo_text)
            crime_mo_rows.append((
                str(uuid.uuid4()), crime_id,
                mo_feats["crime_method"],
                mo_feats["entry_method"],
                mo_feats["target_type"],
                mo_feats["weapon_used"],
                json.dumps(mo_feats["tools_used"]),
                mo_feats["time_of_day"],
                mo_feats["day_type"],
                mo_feats["planning_level"],
                mo_feats["gang_involved"],
                mo_feats["num_accused"],
                mo_feats["escape_method"],
                mo_feats["vehicle_used_in_crime"],
                json.dumps(mo_feats["modus_operandi_tags"]),
                "rule_based",
            ))

            all_crime_ids.append((crime_id, mo_key, crime_type_val, district))

    # Batch insert crimes
    execute_batch(cur, """
        INSERT INTO crimes (
            id, fir_number, crime_type, severity, status,
            district, police_station, location_address,
            latitude, longitude, geom,
            description, mo_text,
            occurred_at, reported_at, registered_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromEWKT(%s),%s,%s,%s,%s,%s)
    """, crime_rows, page_size=200)

    execute_batch(cur, """
        INSERT INTO crime_mo (
            id, crime_id, crime_method, entry_method, target_type,
            weapon_used, tools_used, time_of_day, day_type, planning_level,
            gang_involved, num_accused, escape_method, vehicle_used_in_crime,
            modus_operandi_tags, extraction_method
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, crime_mo_rows, page_size=200)

    conn.commit()
    print(f"  Created {len(crime_rows)} crimes with MO features")

    # ── Victims ────────────────────────────────────────────
    print("\n[4/6] Creating victims...")
    victim_rows = []
    crime_victim_rows = []
    victim_names_pool = [
        "Savitha Devi", "Lakshmi Bai", "Rekha Gowda", "Meena Reddy", "Usha Shetty",
        "Anitha Patil", "Vidya Nair", "Kavitha Rao", "Radha Murthy", "Sujatha Hegde",
        "Ramesh Kumar", "Suresh Naik", "Venkat Swamy", "Prakash Rao", "Kumar Bangera",
        "Mohan Gowda", "Ravi Poojary", "Vijay Shetty", "Santosh Nayak", "Girish Reddy",
        "Nalini Devi", "Padma Bai", "Geeta Kumari", "Champa Gowda", "Saroja Reddy",
    ]

    for crime_id, mo_key, crime_type_val, district in all_crime_ids:
        victim_id = str(uuid.uuid4())
        vname = random.choice(victim_names_pool)
        vage = random.randint(18, 70)
        vgender = random.choice(["female", "female", "male"])  # women more likely in chain snatching
        if mo_key == "chain_snatching":
            vgender = "female"

        victim_rows.append((
            victim_id, vname, vage, vgender,
            random.choice(["Housewife", "Businessman", "Employee", "Student", "Shopkeeper", "Farmer", "Retired"]),
            district, f"Address in {district}", None,
        ))

        injury = "none"
        if mo_key in ("murder",):
            injury = "fatal"
        elif mo_key in ("assault", "robbery", "dacoity"):
            injury = random.choice(["minor", "major", "minor", "none"])

        loss = None
        if mo_key in ("chain_snatching", "house_break_in", "robbery", "dacoity", "fraud", "cyber_fraud_otp", "atm_fraud"):
            loss = random.choice([5000, 10000, 15000, 25000, 50000, 75000, 100000, 150000, 200000])

        crime_victim_rows.append((
            str(uuid.uuid4()), crime_id, victim_id,
            injury, loss, None,
        ))

    execute_batch(cur, """
        INSERT INTO victims (id, name, age, gender, occupation, district, address, contact_number)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, victim_rows, page_size=200)

    execute_batch(cur, """
        INSERT INTO crime_victims (id, crime_id, victim_id, injury_type, loss_amount, loss_description)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, crime_victim_rows, page_size=200)

    conn.commit()
    print(f"  Created {len(victim_rows)} victims")

    # ── Link Criminals to Crimes ────────────────────────────
    print("\n[5/6] Linking criminals to crimes (creating criminal network)...")

    # Map crime type key → gang
    crime_type_to_gang = {
        "chain_snatching":  "Bike Bandit Gang",
        "house_break_in":   "Night Crawlers",
        "cyber_fraud_otp":  "Tech Fraud Gang",
        "atm_fraud":        "Tech Fraud Gang",
        "vehicle_theft":    "Key Masters",
        "dacoity":          "Highway Dacoits",
    }

    crime_criminal_rows = []
    seen_links = set()

    for crime_id, mo_key, crime_type_val, district in all_crime_ids:
        assigned = []

        # 60% chance: link to the relevant gang
        gang_name = crime_type_to_gang.get(mo_key)
        if gang_name and gang_criminals.get(gang_name) and random.random() < 0.60:
            members = gang_criminals[gang_name]
            num_assign = min(random.randint(1, 3), len(members))
            assigned = random.sample(members, num_assign)

        # 25% chance: also add a solo criminal
        if random.random() < 0.25:
            solo_name = random.choice(SOLO_CRIMINALS)["name"]
            solo_id = criminal_ids.get(solo_name)
            if solo_id and solo_id not in assigned:
                assigned.append(solo_id)

        # If nothing assigned: pick 1 random criminal
        if not assigned:
            cid = random.choice(list(criminal_ids.values()))
            assigned = [cid]

        for crim_id in assigned:
            key = (crime_id, crim_id)
            if key in seen_links:
                continue
            seen_links.add(key)
            crime_criminal_rows.append((
                str(uuid.uuid4()), crime_id, crim_id,
                "accused", False, None, None,
            ))

    execute_batch(cur, """
        INSERT INTO crime_criminals (id, crime_id, criminal_id, role, is_arrested, arrest_date, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (crime_id, criminal_id) DO NOTHING
    """, crime_criminal_rows, page_size=200)

    conn.commit()
    print(f"  Created {len(crime_criminal_rows)} crime-criminal links")

    # ── Statistics ─────────────────────────────────────────
    print("\n[6/6] Verification statistics:")
    for table in ["users", "criminals", "crimes", "crime_mo", "victims", "crime_victims", "crime_criminals"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table:<25} {count:>6} records")

    cur.close()
    print("\n✅ Seed complete! Admin login → badge: ADMIN001, password: Admin@2024")
    print("   API docs available at: http://localhost:8000/api/docs")


if __name__ == "__main__":
    print("PAC Karnataka Crime Dataset — Seed Script")
    print("=" * 50)
    print(f"Connecting to: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        seed(conn)
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection failed: {e}")
        print("   Make sure Postgres is running and migrations have been applied:")
        print("   docker exec -it pac_backend alembic upgrade head")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
