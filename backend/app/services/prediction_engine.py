"""
PAC — Prediction Engine

Pure, deterministic risk forecasting and predictive analytics scoring engine.
Exposes modular interfaces to compute criminal risk levels, gang threats,
district risk indexes, hotspot growth profiles, and investigation priority queues.
Allows replacement with ML models (XGBoost/LightGBM) without changing contracts.
"""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Configurable Crime Severity Lookup Table
CRIME_SEVERITY_LOOKUP = {
    "murder": 1.00,
    "attempted murder": 0.95,
    "armed robbery": 0.90,
    "sexual assault": 0.90,
    "kidnapping": 0.85,
    "burglary": 0.55,
    "vehicle theft": 0.45,
    "chain snatching": 0.40,
}


class PredictionEngine:
    """Deterministic, explainable predictive analytics engine."""

    @staticmethod
    def calculate_criminal_risk(
        criminal_data: Dict[str, Any],
        crimes: List[Dict[str, Any]],
        behaviour_profile: Optional[Dict[str, Any]],
        network_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates a deterministic criminal risk score and level based on weighted factors.
        Returns a dict matching the prediction schema.
        """
        # Default fallback values
        severity_score = 0.5
        recency_score = 0.0
        repeat_offending_score = 0.0
        behaviour_consistency = 0.0
        violence_score = 0.0
        gang_influence = 0.0
        network_influence = 0.0
        hotspot_exposure = 0.0
        escalation_score = 0.0

        evidence = []
        now = datetime.now(timezone.utc)

        # 1. Crime Severity Score
        if crimes:
            sev_values = []
            for c in crimes:
                c_type = str(c.get("crime_type", "")).lower()
                sev_values.append(CRIME_SEVERITY_LOOKUP.get(c_type, 0.50))
            severity_score = sum(sev_values) / len(sev_values)
            
            # 2. Recency Score (Exponential Decay)
            # Find latest crime date
            dates = [c.get("occurred_at") for c in crimes if c.get("occurred_at")]
            if dates:
                latest_date = max(dates)
                if isinstance(latest_date, str):
                    try:
                        latest_date = datetime.fromisoformat(latest_date.replace("Z", "+00:00"))
                    except:
                        latest_date = now
                days_elapsed = (now - latest_date).days
                # Decay with 180-day half-life
                recency_score = math.exp(-days_elapsed / 180.0)
                evidence.append(f"Most recent offense was committed {days_elapsed} days ago.")
        else:
            evidence.append("No recorded crimes found.")

        # 3. Repeat Offending Score
        prev_cases = criminal_data.get("previous_cases_count", 0) or 0
        total_cases = max(len(crimes), prev_cases)
        repeat_offending_score = min(1.0, total_cases / 10.0)
        if total_cases > 0:
            evidence.append(f"Offender has {total_cases} total recorded offenses.")

        # 4. Behaviour Consistency & Profile Metrics
        if behaviour_profile:
            score_breakdown = behaviour_profile.get("score_breakdown", {})
            behaviour_consistency = score_breakdown.get("behaviour_consistency_score", 0.0)
            violence_score = score_breakdown.get("violence_score", 0.0)
            gang_influence = score_breakdown.get("gang_affiliation_score", 0.0)
            
            geo_metrics = behaviour_profile.get("geo_metrics", {})
            op_radius = geo_metrics.get("operating_radius_km", 0.0)
            evidence.append(f"Operating radius is limited to {op_radius} km.")

            timeline = behaviour_profile.get("timeline", {})
            if timeline.get("escalation_trend") == "Emerging":
                escalation_score = 0.8
                evidence.append("Crime severity/violence has escalated over the last few offenses.")
            elif timeline.get("escalation_trend") == "Declining":
                escalation_score = 0.2
            else:
                escalation_score = 0.5
        else:
            # Fallbacks if no profile exists
            behaviour_consistency = 0.3
            violence_score = 0.4
            gang_influence = 0.3
            escalation_score = 0.5

        # 5. Neo4j Network Metrics
        co_offenders = network_metrics.get("co_offender_count", 0)
        assoc_strength = network_metrics.get("association_strength", 0.0)
        network_influence = min(1.0, (co_offenders * 0.15) + (assoc_strength * 0.1))
        if co_offenders > 0:
            evidence.append(f"Offender is linked to {co_offenders} co-offenders in Neo4j.")

        # 6. Hotspot Exposure
        # Simple exposure heuristic if active hotspots exist
        hotspots_count = network_metrics.get("hotspots_count", 0)
        hotspot_exposure = min(1.0, hotspots_count * 0.35)
        if hotspots_count > 0:
            evidence.append(f"Active in {hotspots_count} emerging crime hotspots.")

        # 7. Final Weighted Calculation
        risk_score = (
            0.25 * severity_score +
            0.15 * recency_score +
            0.15 * repeat_offending_score +
            0.15 * behaviour_consistency +
            0.10 * violence_score +
            0.10 * gang_influence +
            0.05 * network_influence +
            0.03 * hotspot_exposure +
            0.02 * escalation_score
        )
        risk_score = round(min(1.0, max(0.0, risk_score)), 2)

        # Map to Risk Level
        if risk_score >= 0.76:
            risk_level = "CRITICAL"
        elif risk_score >= 0.51:
            risk_level = "HIGH"
        elif risk_score >= 0.26:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        # Determine Prediction Reason Code
        breakdown = {
            "crime_severity": round(severity_score, 2),
            "recency": round(recency_score, 2),
            "repeat_offending": round(repeat_offending_score, 2),
            "behaviour_consistency": round(behaviour_consistency, 2),
            "violence": round(violence_score, 2),
            "gang_influence": round(gang_influence, 2),
            "network_influence": round(network_influence, 2),
            "hotspot_exposure": round(hotspot_exposure, 2),
            "escalation": round(escalation_score, 2),
        }

        # Select code based on highest contributing weight
        max_factor = max(breakdown, key=breakdown.get)
        reason_map = {
            "crime_severity": "ESCALATING_VIOLENCE",
            "recency": "HOTSPOT_ACTIVITY",
            "repeat_offending": "HIGH_REPEAT_OFFENDER",
            "behaviour_consistency": "SERIAL_PATTERN",
            "violence": "ESCALATING_VIOLENCE",
            "gang_influence": "ACTIVE_GANG_MEMBER",
            "network_influence": "HIGH_NETWORK_INFLUENCE",
            "hotspot_exposure": "HOTSPOT_ACTIVITY",
            "escalation": "ESCALATING_VIOLENCE"
        }
        reason_code = reason_map.get(max_factor, "SERIAL_PATTERN")

        # Confidence Estimation
        confidence = min(0.98, 0.4 + (len(crimes) * 0.05) + (behaviour_consistency * 0.3))

        # Recommendations
        recommendations = [
            "Increase target surveillance and local patrol frequency.",
            "Cross-reference recent unsolved cases matching similar MO characteristics."
        ]
        if co_offenders > 0:
            recommendations.append("Monitor co-offending network and restrict contact links.")
        if gang_influence > 0.5:
            recommendations.append("Coordinate investigation with organized crime divisions.")

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": round(confidence, 2),
            "prediction_reason_code": reason_code,
            "score_breakdown": breakdown,
            "evidence": evidence,
            "recommendations": recommendations
        }

    @staticmethod
    def calculate_district_risk(
        hotspot_count: int,
        crime_volume: int,
        repeat_offender_count: int,
        active_gang_count: int
    ) -> float:
        """
        Calculates District Risk Index (0 - 100).
        Formula: 40% Hotspots + 25% Crime Volume + 20% Repeat Offenders + 15% Gang Activity
        """
        h_score = min(1.0, hotspot_count / 10.0)
        vol_score = min(1.0, crime_volume / 200.0)
        rep_score = min(1.0, repeat_offender_count / 50.0)
        gang_score = min(1.0, active_gang_count / 5.0)

        weighted = (
            0.40 * h_score +
            0.25 * vol_score +
            0.20 * rep_score +
            0.15 * gang_score
        )
        return round(weighted * 100.0, 1)

    @staticmethod
    def forecast_hotspot_growth(
        recent_velocity: float,
        historical_growth: float,
        nearby_influence: float
    ) -> str:
        """
        Forecasts hotspot grow trend: Growing, Stable, or Shrinking.
        Formula: 50% Recent Crime Velocity + 30% Historical Growth + 20% Nearby Influence
        """
        val = (0.50 * recent_velocity) + (0.30 * historical_growth) + (0.20 * nearby_influence)
        if val > 0.60:
            return "Growing"
        elif val < 0.25:
            return "Shrinking"
        return "Stable"

    @staticmethod
    def calculate_gang_threat(
        member_count: int,
        crime_count: int,
        violence_ratio: float,
        network_density: float
    ) -> str:
        """
        Calculates Gang Threat level: LOW, MEDIUM, HIGH, CRITICAL.
        """
        score = (
            min(0.3, member_count * 0.02) +
            min(0.3, crime_count * 0.01) +
            (violence_ratio * 0.25) +
            (network_density * 0.15)
        )
        
        if score >= 0.75:
            return "CRITICAL"
        elif score >= 0.50:
            return "HIGH"
        elif score >= 0.25:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def calculate_investigation_priority(
        severity_score: float,
        behaviour_risk: float,
        gang_threat: float,
        similar_crime_count: int,
        hotspot_risk: float
    ) -> float:
        """
        Calculates Investigation Priority score (1 - 100).
        Formula: 40% Severity + 20% Behaviour Risk + 20% Gang Threat + 10% Similar Crimes + 10% Hotspot Risk
        """
        sim_score = min(1.0, similar_crime_count / 15.0)
        
        weighted = (
            0.40 * severity_score +
            0.20 * behaviour_risk +
            0.20 * gang_threat +
            0.10 * sim_score +
            0.10 * hotspot_risk
        )
        return round(weighted * 100.0, 1)
