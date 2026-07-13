"""
PAC — Standalone Recommendation Engine (Rules-Based)
"""

import logging

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Deterministic rules-based recommendation engine for operational deployments.
    Designed with modularity to allow clean replacement by LLMs in future phases.
    """

    @staticmethod
    def generate_recommendation(
        dominant_crime_type: str,
        peak_time: str,
        risk_level: str,
        repeat_offenders_count: int,
        known_gangs_count: int,
        crime_count: int,
        hotspot_trend: str,
    ) -> str:
        """
        Generates tactical patrol recommendations based on hotspot parameters.
        Returns a detailed operational directive.
        """
        actions = []
        crime_label = dominant_crime_type.replace("_", " ").lower()

        # 1. Base patrol suggestion on dominant crime type and peak time
        if peak_time and peak_time != "unknown":
            actions.append(
                f"High concentration of {crime_label} during peak hours ({peak_time}). "
                f"Increase patrols and set up static visibility points during this window."
            )
        else:
            actions.append(
                f"Concentrated pattern of {crime_label} detected. "
                f"Increase standard sector patrol loops."
            )

        # 2. Risk Level actions
        if risk_level == "High":
            actions.append(
                f"Assessed as High-Risk with {crime_count} total cases. "
                f"Deploy one additional patrol vehicle (Cheetah/Hoysala) to this hotspot zone."
            )

        # 3. Hotspot Trend actions
        if hotspot_trend == "Emerging":
            actions.append(
                f"Hotspot trend is Emerging with recent upward trajectory. "
                f"Deploy preventative sweeps to suppress escalation before the pattern stabilizes."
            )
        elif hotspot_trend == "Declining":
            actions.append(
                f"Hotspot trend is Declining. Maintain baseline patrol visits to prevent resurgence."
            )

        # 3. Offender-specific actions
        if repeat_offenders_count > 0:
            actions.append(
                f"Detected {repeat_offenders_count} known repeat offenders active in this zone. "
                f"Initiate physical door-to-door audits and verify recent whereabouts/activities."
            )

        # 4. Gang-specific actions
        if known_gangs_count > 0:
            actions.append(
                f"Identified activity linked to {known_gangs_count} known gang networks. "
                f"Deploy local Anti-Rowdy/Intelligence squads to monitor key gang meeting points."
            )

        if not actions:
            return "Monitor coordinates for any new registrations. Maintain standard neighborhood beats."

        # Return final combined recommendation
        return " ".join(actions)
