"""
PAC — Behavior Engine

Pure, deterministic scoring engine to analyze a criminal's patterns and build behaviour profiles.
Uses PostgreSQL and CrimeDNA data, enriched with Neo4j network variables.
"""

import math
from typing import List, Dict, Any, Tuple
from collections import Counter
from datetime import datetime
from app.models.crime import Crime, CrimeType, CrimeSeverity
from app.models.criminal import Criminal
from app.models.crime_dna import CrimeDNA


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geodesic distance between two points in km."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class BehaviorEngine:
    """Pure helper to perform explainable calculations on criminal history."""

    @staticmethod
    def analyze(
        criminal: Criminal,
        crimes: List[Crime],
        dnas: List[CrimeDNA],
        network_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs calculations on the historical crimes, DNA records, and network parameters.
        Returns a dict matching the visual schema for the front-end and detailed_metrics JSON.
        """
        total_crimes = len(crimes)
        if total_crimes == 0:
            return {
                "summary": "No crime history found for this profile.",
                "scores": {
                    "risk_score": 0.0,
                    "risk_level": "LOW",
                    "violence_score": 0.0,
                    "gang_affiliation_score": 0.0,
                    "repeat_offender_score": 0.0,
                    "behaviour_consistency_score": 0.0,
                    "serial_offender_probability": 0.0,
                    "behaviour_confidence_score": 0.0,
                },
                "patterns": {},
                "network": network_metrics,
                "geo": {
                    "operating_radius_km": 0.0,
                    "preferred_district": None,
                    "preferred_police_station": None
                },
                "evidence": ["No historical offenses recorded."],
                "recommendations": ["Ensure record status is up to date."],
                "detailed_metrics": {
                    "profile_summary": "No crime history found.",
                    "score_breakdown": {},
                    "patterns": {},
                    "timeline": {},
                    "network_metrics": network_metrics,
                    "geo_metrics": {},
                    "confidence": {},
                    "recommendations": {},
                    "evidence": []
                }
            }

        # Sort crimes by occurred_at
        sorted_crimes = sorted(crimes, key=lambda c: c.occurred_at or datetime.min)
        sorted_dnas = []
        dna_map = {d.crime_id: d for d in dnas}
        for c in sorted_crimes:
            if c.id in dna_map:
                sorted_dnas.append(dna_map[c.id])

        # 1. Frequency Analysis
        intervals = []
        for i in range(1, len(sorted_crimes)):
            c1, c2 = sorted_crimes[i - 1], sorted_crimes[i]
            if c1.occurred_at and c2.occurred_at:
                diff = (c2.occurred_at - c1.occurred_at).days
                intervals.append(max(0, diff))
        avg_interval = float(sum(intervals) / len(intervals)) if intervals else 0.0

        # 2. Time Analysis
        hours = [c.occurred_at.hour for c in sorted_crimes if c.occurred_at]
        preferred_hour = Counter(hours).most_common(1)[0][0] if hours else 12

        time_slots = []
        for c in sorted_crimes:
            if c.occurred_at:
                h = c.occurred_at.hour
                if 5 <= h < 12:
                    time_slots.append("morning")
                elif 12 <= h < 17:
                    time_slots.append("afternoon")
                elif 17 <= h < 22:
                    time_slots.append("evening")
                else:
                    time_slots.append("night")
        preferred_slot = Counter(time_slots).most_common(1)[0][0] if time_slots else "evening"

        days_of_week = [c.occurred_at.strftime("%A") for c in sorted_crimes if c.occurred_at]
        preferred_day = Counter(days_of_week).most_common(1)[0][0] if days_of_week else "Unknown"
        
        weekend_count = sum(1 for c in sorted_crimes if c.occurred_at and c.occurred_at.weekday() in (5, 6))
        weekend_ratio = weekend_count / total_crimes

        months = [c.occurred_at.strftime("%B") for c in sorted_crimes if c.occurred_at]
        preferred_season_month = Counter(months).most_common(1)[0][0] if months else "Unknown"

        # 3. Geographic Analysis
        districts = [c.district for c in sorted_crimes if c.district]
        preferred_district = Counter(districts).most_common(1)[0][0] if districts else "Unknown"

        police_stations = [c.police_station for c in sorted_crimes if c.police_station]
        preferred_police_station = Counter(police_stations).most_common(1)[0][0] if police_stations else "Unknown"

        # Operating radius
        max_dist = 0.0
        coords = [(c.latitude, c.longitude) for c in sorted_crimes if c.latitude is not None and c.longitude is not None]
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                d = haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
                if d > max_dist:
                    max_dist = d
        operating_radius_km = round(max_dist, 2)

        # 4. MO Analysis
        crime_types = [c.crime_type.value for c in sorted_crimes if c.crime_type]
        primary_crime_type = Counter(crime_types).most_common(1)[0][0] if crime_types else "Unknown"

        escape_methods = [d.escape_method for d in sorted_dnas if d.escape_method]
        preferred_escape = Counter(escape_methods).most_common(1)[0][0] if escape_methods else "Unknown"

        target_types = [d.target_type for d in sorted_dnas if d.target_type]
        preferred_target = Counter(target_types).most_common(1)[0][0] if target_types else "Unknown"

        planning_levels = [d.planning_level for d in sorted_dnas if d.planning_level]
        preferred_planning = Counter(planning_levels).most_common(1)[0][0] if planning_levels else "planned"

        all_mo_tags = []
        for d in sorted_dnas:
            if d.modus_operandi_tags:
                all_mo_tags.extend(d.modus_operandi_tags)
        top_mo_tags = [t[0] for t in Counter(all_mo_tags).most_common(5)]

        # 5. Scores Calculation
        # Violence Score: Based on severity (CRITICAL=1.0, HIGH=0.7, MEDIUM=0.4, LOW=0.1) and weapons used
        violence_points = 0.0
        severe_count = 0
        for c in sorted_crimes:
            if c.severity == CrimeSeverity.CRITICAL:
                violence_points += 1.0
                severe_count += 1
            elif c.severity == CrimeSeverity.HIGH:
                violence_points += 0.7
                severe_count += 1
            elif c.severity == CrimeSeverity.MEDIUM:
                violence_points += 0.4
            else:
                violence_points += 0.1
        
        # Additional points for weapons used
        weapon_crimes = sum(1 for d in sorted_dnas if d.weapon_used and d.weapon_used.lower() not in ("none", "null", ""))
        violence_points += weapon_crimes * 0.3
        violence_score = min(1.0, violence_points / max(1.0, total_crimes))

        # Gang Affiliation Score: based on Neo4j gang participation or co-offender links
        co_offenders = network_metrics.get("co_offender_count", 0)
        gang_affiliation = 0.0
        if criminal.gang_affiliation or criminal.gang_name:
            gang_affiliation = 1.0
        elif co_offenders > 0:
            gang_affiliation = min(1.0, 0.3 + (co_offenders * 0.1))

        # Repeat Offender Score
        prev_cases = criminal.previous_cases_count or 0
        actual_cases = total_crimes
        combined_cases = max(prev_cases, actual_cases)
        repeat_score = min(1.0, combined_cases / 10.0)

        # Behaviour Consistency Score: based on entropy of crime types, slots, and districts
        # Higher consistency if they keep committing same crime types, in same district, same slot
        unique_types = len(set(crime_types))
        unique_districts = len(set(districts))
        unique_slots = len(set(time_slots))
        
        consistency_val = (1.0 / unique_types) * 0.4 + (1.0 / unique_districts) * 0.3 + (1.0 / unique_slots) * 0.3
        behaviour_consistency_score = min(1.0, consistency_val)

        # Escalation Trend
        escalation_trend = "Stable"
        if len(sorted_crimes) >= 2:
            mid = len(sorted_crimes) // 2
            first_half = sorted_crimes[:mid]
            second_half = sorted_crimes[mid:]
            
            def get_avg_severity(c_list):
                score_map = {CrimeSeverity.LOW: 1, CrimeSeverity.MEDIUM: 2, CrimeSeverity.HIGH: 3, CrimeSeverity.CRITICAL: 4}
                vals = [score_map.get(c.severity, 2) for c in c_list]
                return sum(vals) / len(vals)
                
            first_sev = get_avg_severity(first_half)
            second_sev = get_avg_severity(second_half)
            if second_sev > first_sev + 0.3:
                escalation_trend = "Emerging"
            elif second_sev < first_sev - 0.3:
                escalation_trend = "Declining"

        # Serial Offender Probability
        serial_prob = 0.0
        if total_crimes >= 3 and behaviour_consistency_score > 0.6:
            serial_prob = min(0.95, 0.4 + (total_crimes * 0.05) + (behaviour_consistency_score * 0.3))
            if operating_radius_km < 10.0:
                serial_prob = min(0.98, serial_prob + 0.1)

        # Risk Score (0.0 - 1.0)
        risk_score = (violence_score * 0.4) + (repeat_score * 0.3) + (gang_affiliation * 0.15) + (behaviour_consistency_score * 0.15)
        if escalation_trend == "Emerging":
            risk_score = min(1.0, risk_score + 0.05)
        risk_score = min(1.0, max(0.0, risk_score))

        if risk_score >= 0.70:
            risk_level = "HIGH"
        elif risk_score >= 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Confidence Score
        confidence_val = min(0.98, 0.3 + (total_crimes * 0.1) + (behaviour_consistency_score * 0.2))

        # 6. Detailed Explanations & Evidence Generation
        evidence = []
        evidence.append(f"Committed {total_crimes} total offenses of type '{primary_crime_type}'.")
        if avg_interval > 0:
            evidence.append(f"Average strike interval is {avg_interval:.1f} days.")
        
        slot_percentage = int((time_slots.count(preferred_slot) / max(1, len(time_slots))) * 100)
        evidence.append(f"{slot_percentage}% of crimes committed during the {preferred_slot} hours.")
        
        district_percentage = int((districts.count(preferred_district) / max(1, len(districts))) * 100)
        evidence.append(f"{district_percentage}% of activity centered in district '{preferred_district}'.")
        
        evidence.append(f"Operating radius is restricted to {operating_radius_km} km.")
        
        if co_offenders > 0:
            evidence.append(f"Associated with {co_offenders} co-offenders.")
            if network_metrics.get("strongest_associate"):
                evidence.append(f"Strongest co-offending link is with {network_metrics['strongest_associate']} (Strength: {network_metrics['association_strength']}).")
        if criminal.gang_name:
            evidence.append(f"Member of gang '{criminal.gang_name}'.")

        # Generate summary
        summary = (
            f"Primary offender profile: operates mainly in {preferred_district} (specifically {preferred_police_station}). "
            f"Prefers {primary_crime_type} crimes targeting {preferred_target}. "
            f"Highly active during {preferred_slot} hours, particularly on {preferred_day}s. "
            f"Shows a behaviour consistency of {behaviour_consistency_score:.2f} with an escalation trend identified as {escalation_trend}."
        )

        detailed_metrics = {
            "profile_summary": summary,
            "score_breakdown": {
                "violence_score": round(violence_score, 2),
                "gang_affiliation_score": round(gang_affiliation, 2),
                "repeat_offender_score": round(repeat_score, 2),
                "behaviour_consistency_score": round(behaviour_consistency_score, 2),
                "serial_offender_probability": round(serial_prob, 2),
                "risk_score": round(risk_score, 2),
                "risk_level": risk_level
            },
            "patterns": {
                "preferred_time_slot": preferred_slot,
                "preferred_day_of_week": preferred_day,
                "preferred_season_month": preferred_season_month,
                "preferred_escape_method": preferred_escape,
                "preferred_target_type": preferred_target,
                "preferred_planning_level": preferred_planning,
                "modus_operandi_tags": top_mo_tags
            },
            "timeline": {
                "avg_crime_interval_days": round(avg_interval, 1),
                "escalation_trend": escalation_trend,
                "total_recorded_crimes": total_crimes
            },
            "network_metrics": network_metrics,
            "geo_metrics": {
                "operating_radius_km": operating_radius_km,
                "preferred_district": preferred_district,
                "preferred_police_station": preferred_police_station
            },
            "confidence": {
                "confidence_score": round(confidence_val, 2),
                "confidence_explanation": f"Calculated based on a crime pool of size {total_crimes} with consistency index {behaviour_consistency_score:.2f}."
            },
            "recommendations": [
                f"Deploy regular patrols in {preferred_police_station} station limits during {preferred_slot} hours.",
                "Cross-reference new MO filings matching tags: " + ", ".join(top_mo_tags[:3])
            ],
            "evidence": evidence
        }

        return {
            "summary": summary,
            "scores": {
                "risk_score": round(risk_score, 2),
                "risk_level": risk_level,
                "violence_score": round(violence_score, 2),
                "gang_affiliation_score": round(gang_affiliation, 2),
                "repeat_offender_score": round(repeat_score, 2),
                "behaviour_consistency_score": round(behaviour_consistency_score, 2),
                "serial_offender_probability": round(serial_prob, 2),
                "behaviour_confidence_score": round(confidence_val, 2)
            },
            "patterns": {
                "primary_crime_type": primary_crime_type,
                "preferred_time_slot": preferred_slot,
                "preferred_day_of_week": preferred_day,
                "preferred_season_month": preferred_season_month,
                "preferred_escape_method": preferred_escape,
                "preferred_target_type": preferred_target,
                "preferred_planning_level": preferred_planning,
                "modus_operandi_tags": top_mo_tags
            },
            "network": network_metrics,
            "geo": {
                "operating_radius_km": operating_radius_km,
                "preferred_district": preferred_district,
                "preferred_police_station": preferred_police_station
            },
            "evidence": evidence,
            "recommendations": detailed_metrics["recommendations"],
            "detailed_metrics": detailed_metrics
        }
