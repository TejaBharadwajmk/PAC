"""
PAC — MO Feature Extraction Service (Rule-Based)

Extracts structured Modus Operandi features from free-text crime narratives.

Strategy:
  • Pure keyword matching — fast, deterministic, zero API cost
  • Covers: crime method, entry method, target type, weapons, tools,
    time of day, planning level, gang detection, escape method
  • Complements Sentence Transformer embeddings:
      - Embeddings = semantic similarity (finds behaviourally similar crimes)
      - MO features = structured filters (narrow down by specific attributes)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Keyword Maps ───────────────────────────────────────────

CRIME_METHODS: Dict[str, List[str]] = {
    "forced_entry": ["broke", "forced", "damaged", "smashed", "kicked", "drilled", "cut grill", "cut lock", "broken"],
    "stealth": ["silently", "sneaked", "crept", "quietly", "without notice", "undetected", "while sleeping"],
    "deception": ["impersonated", "pretended", "disguised", "lured", "cheated", "posed as", "fake call", "misrepresented"],
    "cyber": ["online", "internet", "phishing", "hacked", "otp", "link", "skimm", "card clone", "upi", "qr code", "remote access"],
    "confrontation": ["snatched", "grabbed", "robbed", "attacked", "assaulted", "threatened", "intercepted", "blocked path"],
    "opportunistic": ["found unlocked", "left unattended", "abandoned", "open vehicle", "unguarded"],
}

ENTRY_METHODS: Dict[str, List[str]] = {
    "rear_window": ["rear window", "back window", "backside window", "window glass", "window grill"],
    "front_door": ["front door", "main door", "main entrance", "front entrance"],
    "back_door": ["back door", "rear door", "backside door", "back entrance"],
    "roof": ["roof", "ceiling", "from top", "rooftop", "terrace"],
    "compound_wall": ["compound wall", "boundary wall", "jumped over", "scaled the wall"],
    "online": ["online", "internet", "website", "app", "link", "email"],
    "atm": ["atm", "card machine", "skimmer device", "kiosk"],
    "direct": ["directly approached", "walked in", "entered directly", "without breaking"],
}

TIME_PATTERNS: Dict[str, List[str]] = {
    "late_night": ["2am", "3am", "4am", "midnight", "late night", "wee hours", "1am", "0200", "0300", "0400", "00:"],
    "night": ["night", "10pm", "11pm", "9pm", "dark", "after dark", "nighttime", "22:00", "23:00", "21:00"],
    "evening": ["evening", "dusk", "5pm", "6pm", "7pm", "8pm", "sunset", "17:00", "18:00", "19:00", "20:00"],
    "morning": ["morning", "dawn", "6am", "7am", "8am", "9am", "sunrise", "early morning", "06:00", "07:00", "08:00"],
    "afternoon": ["afternoon", "noon", "12pm", "1pm", "2pm", "3pm", "midday", "12:00", "13:00", "14:00", "15:00"],
}

WEAPON_PATTERNS: Dict[str, List[str]] = {
    "knife": ["knife", "blade", "dagger", "sharp weapon", "kathi", "sharp object"],
    "gun": ["gun", "pistol", "revolver", "firearm", "country bomb", "pistol", "armed"],
    "iron_rod": ["iron rod", "rod", "pipe", "crowbar", "iron bar", "lathi", "stick"],
    "acid": ["acid", "chemical substance", "corrosive"],
}

TOOL_PATTERNS: Dict[str, List[str]] = {
    "crowbar": ["crowbar", "jemmy", "jimmy"],
    "duplicate_key": ["duplicate key", "master key", "fake key", "spare key"],
    "wire": ["wire", "hotwire", "two wire", "bypass"],
    "screwdriver": ["screwdriver", "screw driver"],
    "drill": ["drill", "drilled hole"],
    "skimmer": ["skimmer", "skimming device", "card reader device", "overlay"],
    "mobile_phone": ["mobile", "phone call", "whatsapp", "sms link"],
    "rope": ["rope", "tied up", "bound"],
}

ESCAPE_METHODS: Dict[str, List[str]] = {
    "bike": ["bike", "motorcycle", "two-wheeler", "two wheeler", "motorbike", "scooter", "pulsar", "activa", "splendor"],
    "car": ["car", "four-wheeler", "four wheeler", "vehicle", "suv", "sedan", "auto rickshaw", "auto"],
    "foot": ["foot", "ran away on foot", "fled on foot", "escaped on foot", "ran through"],
}

# NOTE: Order matters — first match wins. More specific types must come before 'individual'.
TARGET_TYPES: Dict[str, List[str]] = {
    "atm": ["atm", "atm machine", "cash machine", "kiosk"],
    "gold_shop": ["gold shop", "jewellery shop", "jeweler", "jewellers"],
    "bank": ["bank", "financial institution", "cooperative bank"],
    "factory": ["factory", "warehouse", "godown", "industry", "plant"],
    "vehicle": ["vehicle", "parked car", "parked bike", "two-wheeler parked", "car parked"],
    "residence": ["house", "home", "flat", "apartment", "residence", "dwelling", "bungalow", "villa"],
    "shop": ["shop", "store", "establishment", "outlet", "business", "showroom", "hotel", "restaurant"],
    # 'individual' last so it only matches when nothing more specific was found
    "individual": ["woman", "man", "lady", "pedestrian", "victim walking", "passerby", "old woman", "old man"],
}


def _match_first(text: str, patterns: Dict[str, List[str]]) -> Optional[str]:
    text_lower = text.lower()
    for category, keywords in patterns.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def _extract_all_tools(text: str) -> List[str]:
    text_lower = text.lower()
    return [
        tool for tool, keywords in TOOL_PATTERNS.items()
        if any(kw in text_lower for kw in keywords)
    ]


def _detect_gang_and_count(text: str) -> Tuple[bool, int]:
    text_lower = text.lower()

    # Explicit number extraction
    num_match = re.search(
        r"(\d+)\s*(?:accused|persons|suspects|individuals|gang members|members)",
        text_lower
    )
    if num_match:
        n = int(num_match.group(1))
        return n > 1, n

    # Word number detection
    word_nums = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    for word, num in word_nums.items():
        if word in text_lower and any(
            kw in text_lower
            for kw in ["accused", "persons", "suspects", "members"]
        ):
            return True, num

    gang_kws = ["gang", "group of", "team of", "organised", "organized"]
    if any(kw in text_lower for kw in gang_kws):
        return True, 3

    return False, 1


def _infer_planning_level(text: str, crime_type: str) -> str:
    text_lower = text.lower()
    high = ["pre-planned", "pre planned", "surveyed", "reconnoitred", "systematically", "planned in advance"]
    medium = ["waited", "disguised", "followed victim", "duplicate key", "skimmer", "tampered", "observed"]

    if any(kw in text_lower for kw in high):
        return "highly_planned"
    if any(kw in text_lower for kw in medium) or crime_type in [
        "cyber_crime", "atm_fraud", "fraud", "kidnapping"
    ]:
        return "planned"
    return "opportunistic"


def _build_tags(text: str, crime_type: str, features: dict) -> List[str]:
    text_lower = text.lower()
    tags: List[str] = []

    if features.get("vehicle_used_in_crime"):
        tags.append("vehicle_used")
    if features.get("time_of_day") in ["night", "late_night"]:
        tags.append("night_operation")
    if features.get("gang_involved"):
        tags.append("gang_crime")
    if (features.get("num_accused") or 1) >= 3:
        tags.append("large_gang")
    if features.get("target_type") == "residence":
        tags.append("residential")
    if features.get("target_type") in ["bank", "atm", "gold_shop"]:
        tags.append("high_value_target")
    if any(kw in text_lower for kw in ["gold", "jewellery", "jewelry", "chain", "necklace", "bangles"]):
        tags.append("gold_theft")
    if any(kw in text_lower for kw in ["bike", "motorcycle", "two-wheeler"]):
        tags.append("two_wheeler")
    if features.get("planning_level") in ["planned", "highly_planned"]:
        tags.append("premeditated")
    if crime_type in ["cyber_crime", "atm_fraud", "fraud"]:
        tags.append("financial_fraud")

    return list(set(tags))


# Default crime_method per crime type when keyword matching fails
_CRIME_TYPE_DEFAULT_METHOD: Dict[str, str] = {
    "chain_snatching": "confrontation",
    "robbery": "confrontation",
    "assault": "confrontation",
    "murder": "confrontation",
    "kidnapping": "confrontation",
    "dacoity": "confrontation",
    "house_break_in": "forced_entry",
    "burglary": "forced_entry",
    "cyber_crime": "cyber",
    "atm_fraud": "cyber",
    "fraud": "deception",
    "drug_offense": "opportunistic",
    "theft": "opportunistic",
    "vehicle_theft": "opportunistic",
    "auto_theft": "opportunistic",
    "extortion": "confrontation",
    "sexual_assault": "confrontation",
}


def extract_mo_features(mo_text: str, crime_type: str) -> dict:
    """
    Extract structured MO features from free-text crime narrative.

    Returns a dict compatible with CrimeMOCreate schema.
    Fast, deterministic, no external API calls.
    """
    try:
        gang_involved, num_accused = _detect_gang_and_count(mo_text)
        escape = _match_first(mo_text, ESCAPE_METHODS) or "unknown"
        vehicle_used = escape in ("bike", "car") or any(
            kw in mo_text.lower()
            for kw in ["bike", "motorcycle", "car", "vehicle", "two-wheeler"]
        )

        # Use keyword match; fall back to per-crime-type default; then 'unknown'
        crime_method = (
            _match_first(mo_text, CRIME_METHODS)
            or _CRIME_TYPE_DEFAULT_METHOD.get(crime_type)
            or "unknown"
        )

        features: dict = {
            "crime_method": crime_method,
            "entry_method": _match_first(mo_text, ENTRY_METHODS) or "unknown",
            "target_type": _match_first(mo_text, TARGET_TYPES) or "unknown",
            "weapon_used": _match_first(mo_text, WEAPON_PATTERNS) or "none",
            "tools_used": _extract_all_tools(mo_text),
            "time_of_day": _match_first(mo_text, TIME_PATTERNS) or "unknown",
            "day_type": "unknown",
            "planning_level": _infer_planning_level(mo_text, crime_type),
            "gang_involved": gang_involved,
            "num_accused": num_accused,
            "escape_method": escape,
            "vehicle_used_in_crime": vehicle_used,
        }
        features["modus_operandi_tags"] = _build_tags(mo_text, crime_type, features)
        return features

    except Exception as exc:
        logger.error(f"MO extraction failed: {exc}", exc_info=True)
        return {}
