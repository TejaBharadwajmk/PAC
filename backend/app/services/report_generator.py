"""
PAC — Investigation Report Generator

Generates 5 structured police intelligence report types from assembled
PAC context.  Reports are designed for PDF export in a future phase.

All report content is derived exclusively from PAC intelligence modules.
Reports are structured documents, not conversational responses.

Supported report types:
  - fir_investigation   : Crime / FIR Investigation Report
  - criminal_intelligence : Criminal Intelligence Report
  - district_crime       : District Crime Intelligence Report
  - hotspot_assessment   : Hotspot Assessment Report
  - gang_intelligence    : Gang Intelligence Report

Each report follows the same section structure:
  1. Executive Summary
  2. Key Findings
  3. Evidence
  4. Risk Assessment
  5. Recommendations
  6. Suggested Next Actions
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates structured intelligence reports from PAC context."""

    SUPPORTED_TYPES = [
        "fir_investigation",
        "criminal_intelligence",
        "district_crime",
        "hotspot_assessment",
        "gang_intelligence",
    ]

    def __init__(self, llm_provider=None) -> None:
        """
        Args:
            llm_provider: Optional BaseLLM instance for AI-enhanced narrative sections.
                          If None, reports are generated deterministically.
        """
        self.llm = llm_provider

    async def generate(
        self,
        report_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a structured intelligence report.

        Args:
            report_type: One of the 5 supported report types.
            context:     Structured PAC context from ContextBuilder.

        Returns:
            Structured report dict with all 6 sections.
        """
        if report_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported report type: '{report_type}'. "
                f"Supported: {self.SUPPORTED_TYPES}"
            )

        handler = getattr(self, f"_report_{report_type}")
        report = await handler(context)

        report["metadata"] = {
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_sources": context.get("data_sources", []),
            "evidence_count": len(context.get("evidence", [])),
            "pac_version": "4.1",
        }

        logger.info(
            f"ReportGenerator: generated '{report_type}' report with "
            f"{len(context.get('evidence', []))} evidence items."
        )
        return report

    # ── FIR Investigation Report ───────────────────────────────────────────────

    async def _report_fir_investigation(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        crime = ctx.get("crime_summary", {})
        similar = ctx.get("similar_cases", [])
        behaviour = ctx.get("behaviour", {})
        prediction = ctx.get("prediction", {})
        network = ctx.get("network", {})
        evidence = ctx.get("evidence", [])

        crime_method = crime.get("crime_method", "Not recorded")
        target_type = crime.get("target_type", "Not recorded")
        risk_level = behaviour.get("risk_level") or prediction.get(
            "criminal_risk", {}
        ).get("risk_level", "UNKNOWN")

        executive_summary = (
            f"This FIR Investigation Report was generated from PAC intelligence modules. "
            f"The recorded crime involves {crime_method.replace('_', ' ')} targeting "
            f"{target_type.replace('_', ' ')} victims. "
            f"The primary suspect is classified as {risk_level} risk. "
            f"{len(similar)} similar historical cases have been identified."
        )

        key_findings = _list_from_non_empty([
            f"Crime method: {crime_method.replace('_', ' ')}",
            f"Target type: {target_type.replace('_', ' ')}",
            f"Time of operation: {crime.get('time_of_day_slot', 'Unknown')}",
            f"Gang involvement: {'Yes' if crime.get('gang_involved') else 'No/Unknown'}",
            f"Planning level: {crime.get('planning_level', 'Unknown')}",
            f"Similar cases identified: {len(similar)}",
            f"Primary suspect risk level: {risk_level}",
        ])

        risk_assessment = _build_risk_assessment(behaviour, prediction)
        recs = ctx.get("recommendations", [])
        if not recs:
            recs = [
                "Conduct forensic similarity search across regional crime database.",
                "Interview witnesses in the identified hotspot area.",
                "Cross-reference escape route with known gang operational patterns.",
            ]

        return {
            "title": "FIR Investigation Intelligence Report",
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "evidence": evidence[:10],
            "risk_assessment": risk_assessment,
            "recommendations": recs[:5],
            "suggested_next_actions": [
                "1. Assign case to dedicated detective with serial-crime experience.",
                "2. Run full DNA similarity search against regional database.",
                "3. Request CCTV footage from identified hotspot coordinates.",
                "4. Cross-reference suspect with Neo4j criminal network.",
                "5. File charge sheet within 48 hours if suspect is arrested.",
            ],
        }

    # ── Criminal Intelligence Report ───────────────────────────────────────────

    async def _report_criminal_intelligence(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        behaviour = ctx.get("behaviour", {})
        prediction = ctx.get("prediction", {})
        network = ctx.get("network", {})
        evidence = ctx.get("evidence", [])

        risk_level = behaviour.get("risk_level", "UNKNOWN")
        primary_crime = behaviour.get("primary_crime_type", "Not identified")
        escalation = behaviour.get("escalation_trend", "Unknown")
        violence = behaviour.get("violence_score", 0.0)
        gang_score = behaviour.get("gang_affiliation_score", 0.0)
        radius = behaviour.get("operating_radius_km", 0.0)
        co_offenders = network.get("co_offenders", [])

        executive_summary = (
            f"This Criminal Intelligence Report is generated from PAC Behaviour, "
            f"Network, and Predictive Intelligence modules. "
            f"The subject is a {risk_level} risk offender primarily linked to "
            f"{primary_crime.replace('_', ' ')} offences. "
            f"Escalation trend is {escalation}. "
            f"{len(co_offenders)} criminal associates identified in Neo4j network."
        )

        key_findings = _list_from_non_empty([
            f"Risk classification: {risk_level}",
            f"Primary crime type: {primary_crime.replace('_', ' ')}",
            f"Operating radius: {radius:.1f} km",
            f"Violence index: {violence:.2f}",
            f"Gang affiliation score: {gang_score:.2f}",
            f"Escalation trend: {escalation}",
            f"Co-offender network size: {len(co_offenders)}",
            f"Preferred operating time: {behaviour.get('preferred_time_slot', 'Unknown')}",
            f"Primary operating district: {behaviour.get('preferred_district', 'Unknown')}",
        ])

        risk_assessment = _build_risk_assessment(behaviour, prediction)
        recs = ctx.get("recommendations", [])
        if not recs:
            recs = [
                "Place subject under active surveillance immediately.",
                "Map all known associates for coordinated arrest operation.",
                "Establish patrol coverage of identified operating district.",
            ]

        return {
            "title": "Criminal Intelligence Report",
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "evidence": evidence[:12],
            "risk_assessment": risk_assessment,
            "recommendations": recs[:5],
            "suggested_next_actions": [
                "1. Initiate targeted surveillance of subject's operating radius.",
                "2. Conduct network disruption by arresting highest-strength associates.",
                "3. Issue district alert to police stations in operating zone.",
                "4. Request background check on gang affiliations.",
                "5. Schedule bi-weekly intelligence review of subject activity.",
            ],
        }

    # ── District Crime Report ──────────────────────────────────────────────────

    async def _report_district_crime(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        geo = ctx.get("geo", {})
        prediction = ctx.get("prediction", {})
        entities = ctx.get("entities", {})
        evidence = ctx.get("evidence", [])

        district = entities.get("district") or geo.get("district_filter") or "Unknown District"
        hotspots = geo.get("hotspots", [])
        total_hs = geo.get("total_hotspots", len(hotspots))
        dist_risk = prediction.get("district_risk", {})
        risk_level = dist_risk.get("risk_level", "UNKNOWN")
        dist_score = dist_risk.get("score", 0.0)

        dominant_types = list({h.get("dominant_crime_type", "?") for h in hotspots if h.get("dominant_crime_type")})
        growing_hs = [h for h in hotspots if h.get("trend") == "Emerging"]

        executive_summary = (
            f"District Crime Intelligence Report for {district}. "
            f"Risk index: {dist_score:.1f} ({risk_level}). "
            f"{total_hs} active crime hotspots identified, "
            f"{len(growing_hs)} showing growing trend. "
            f"Primary crime types: {', '.join(dominant_types[:3]) or 'Not specified'}."
        )

        key_findings = _list_from_non_empty([
            f"District risk level: {risk_level}",
            f"Risk score: {dist_score:.1f}",
            f"Total active hotspots: {total_hs}",
            f"Growing hotspots: {len(growing_hs)}",
            f"Primary crime types: {', '.join(dominant_types[:3]) or 'Unknown'}",
        ] + [
            f"Hotspot #{h.get('cluster_id')}: {h.get('dominant_crime_type')} — {h.get('trend')}"
            for h in hotspots[:5]
        ])

        risk_assessment = {
            "district": district,
            "risk_level": risk_level,
            "risk_score": dist_score,
            "evidence": dist_risk.get("evidence", []),
        }

        recs = dist_risk.get("recommendations", []) + ctx.get("recommendations", [])
        if not recs:
            recs = [
                f"Increase patrol density in growing hotspots of {district}.",
                "Deploy mobile checkpoints during peak crime hours.",
                "Coordinate with adjacent districts on spillover crime patterns.",
            ]

        return {
            "title": f"District Crime Intelligence Report — {district}",
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "evidence": evidence[:10],
            "risk_assessment": risk_assessment,
            "recommendations": list(dict.fromkeys(recs))[:5],
            "suggested_next_actions": [
                f"1. Deploy tactical patrol units to {len(growing_hs)} growing hotspots.",
                "2. Activate community policing programme in high-risk zones.",
                "3. Coordinate intelligence sharing with adjacent district SPs.",
                "4. Review CCTV coverage of top 3 hotspot clusters.",
                "5. Schedule monthly crime intelligence review meeting.",
            ],
        }

    # ── Hotspot Assessment Report ──────────────────────────────────────────────

    async def _report_hotspot_assessment(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        geo = ctx.get("geo", {})
        prediction = ctx.get("prediction", {})
        evidence = ctx.get("evidence", [])
        hotspots = geo.get("hotspots", [])

        high_risk_hs = [h for h in hotspots if h.get("risk_level") == "High"]
        emerging_hs  = [h for h in hotspots if h.get("trend") == "Emerging"]

        executive_summary = (
            f"Geospatial Hotspot Assessment identifies {len(hotspots)} active crime clusters. "
            f"{len(high_risk_hs)} are classified High Risk. "
            f"{len(emerging_hs)} are showing Emerging/Growing trends, requiring immediate attention."
        )

        key_findings = _list_from_non_empty([
            f"Total hotspots detected: {len(hotspots)}",
            f"High risk clusters: {len(high_risk_hs)}",
            f"Emerging trend clusters: {len(emerging_hs)}",
        ] + [
            f"Hotspot #{h.get('cluster_id')}: {h.get('crime_count')} crimes, "
            f"{h.get('dominant_crime_type')}, peak={h.get('peak_time')}, trend={h.get('trend')}"
            for h in hotspots[:8]
        ])

        patrol_recommendations = [
            f"Hotspot #{h.get('cluster_id')}: Deploy patrols {h.get('patrol_window', 'as needed')} — {h.get('recommendation', '')}"
            for h in hotspots[:5]
        ]

        return {
            "title": "Hotspot Assessment Report",
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "evidence": evidence[:10],
            "risk_assessment": {
                "total_hotspots": len(hotspots),
                "high_risk_count": len(high_risk_hs),
                "emerging_count": len(emerging_hs),
            },
            "recommendations": patrol_recommendations[:5] or [
                "Deploy dynamic patrols to highest density crime clusters.",
                "Establish fixed checkpoints at emerging hotspot perimeters.",
            ],
            "suggested_next_actions": [
                "1. Brief beat officers with hotspot coordinates and peak time windows.",
                "2. Position marked vehicles visibly in top 3 high-risk clusters.",
                "3. Set up automatic alerts for new crimes in growing clusters.",
                "4. Review hotspot data weekly and adjust patrol strategy.",
                "5. Share geo intelligence with traffic police for road blockage coordination.",
            ],
        }

    # ── Gang Intelligence Report ───────────────────────────────────────────────

    async def _report_gang_intelligence(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        network = ctx.get("network", {})
        prediction = ctx.get("prediction", {})
        entities = ctx.get("entities", {})
        evidence = ctx.get("evidence", [])

        gang_name = entities.get("gang_name", "Unknown Gang")
        gang_threat = prediction.get("gang_threat", {})
        threat_level = gang_threat.get("threat_level", "UNKNOWN")
        threat_score = gang_threat.get("score", 0.0)
        members = network.get("gang_members", [])

        executive_summary = (
            f"Gang Intelligence Report for {gang_name}. "
            f"Threat level: {threat_level} (score: {threat_score:.1f}). "
            f"{len(members)} active members identified in PAC network. "
            f"Operational data sourced from Neo4j criminal network and predictive intelligence."
        )

        key_findings = _list_from_non_empty([
            f"Gang designation: {gang_name}",
            f"Threat level: {threat_level}",
            f"Threat score: {threat_score:.1f}",
            f"Active members in PAC database: {len(members)}",
        ] + gang_threat.get("evidence", []))

        recs = gang_threat.get("recommendations", []) + ctx.get("recommendations", [])
        if not recs:
            recs = [
                "Initiate targeted surveillance of top 3 gang leaders.",
                "Coordinate multi-offender arrest operation with SIT.",
                "Freeze assets and investigate gang funding sources.",
            ]

        return {
            "title": f"Gang Intelligence Report — {gang_name}",
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "evidence": evidence[:10],
            "risk_assessment": {
                "gang_name": gang_name,
                "threat_level": threat_level,
                "threat_score": threat_score,
                "member_count": len(members),
            },
            "recommendations": list(dict.fromkeys(recs))[:5],
            "suggested_next_actions": [
                "1. Brief DCRB / SIT on gang threat level and member roster.",
                "2. Initiate covert surveillance on identified gang members.",
                "3. Issue lookout notices for members with active warrants.",
                "4. Coordinate with cybercrime unit on digital communication monitoring.",
                "5. Schedule fortnightly gang intelligence review with DCP office.",
            ],
        }


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _list_from_non_empty(items: List[Optional[str]]) -> List[str]:
    """Filter out None/empty items from a list."""
    return [item for item in items if item]


def _build_risk_assessment(
    behaviour: Dict[str, Any],
    prediction: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a standardised risk assessment section from behaviour + prediction data."""
    crim_risk = prediction.get("criminal_risk", {})
    return {
        "risk_level": behaviour.get("risk_level") or crim_risk.get("risk_level", "UNKNOWN"),
        "risk_score": behaviour.get("risk_score") or crim_risk.get("score", 0.0),
        "confidence": crim_risk.get("confidence", 0.0),
        "reason_code": crim_risk.get("reason_code", ""),
        "escalation_trend": behaviour.get("escalation_trend", "Unknown"),
        "violence_score": behaviour.get("violence_score", 0.0),
        "gang_affiliation_score": behaviour.get("gang_affiliation_score", 0.0),
    }
