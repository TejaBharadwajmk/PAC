"""
PAC — Geo Intelligence Schemas (Pydantic v2)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HotspotResponse(BaseModel):
    """Details of a single crime hotspot cluster identified via PostGIS DBSCAN."""
    cluster_id: int = Field(..., description="Unique ID for the spatial cluster")
    center_latitude: float = Field(..., description="Latitude of the hotspot centroid")
    center_longitude: float = Field(..., description="Longitude of the hotspot centroid")
    radius_meters: float = Field(..., description="Spatial radius of the hotspot in meters")
    crime_count: int = Field(..., description="Number of crimes in this cluster")
    dominant_crime_type: str = Field(..., description="Dominant crime category in this hotspot")
    peak_time: str = Field(..., description="Time of day when crimes peak in this hotspot")
    suggested_patrol_window: str = Field(..., description="Rule-based suggested operational patrol window")
    hotspot_trend: str = Field(..., description="Trend classification: Emerging, Stable, or Declining")
    confidence_score: float = Field(..., description="Confidence rating of the hotspot (0.0 to 1.0)")
    risk_level: str = Field(..., description="Assessed risk level: Low, Medium, or High")
    repeat_offenders_count: int = Field(..., description="Count of known repeat offenders active in this hotspot")
    known_gangs_count: int = Field(..., description="Count of distinct gangs active in this hotspot")
    recommendation: str = Field(..., description="Tactical deterministic recommendation for patrols")

    model_config = {
        "json_schema_extra": {
            "example": {
                "cluster_id": 0,
                "center_latitude": 12.9331,
                "center_longitude": 77.6515,
                "radius_meters": 350.5,
                "crime_count": 14,
                "dominant_crime_type": "chain_snatching",
                "peak_time": "18:00-22:00",
                "suggested_patrol_window": "17:30-22:30",
                "hotspot_trend": "Emerging",
                "confidence_score": 0.85,
                "risk_level": "High",
                "repeat_offenders_count": 3,
                "known_gangs_count": 1,
                "recommendation": "High concentration of chain snatching between 6 PM–10 PM. Increase evening patrols..."
            }
        }
    }


class GeoStatisticsResponse(BaseModel):
    """High-level summary of spatial intelligence across analyzed records."""
    total_crimes_analyzed: int = Field(..., description="Total spatial crime coordinates scanned")
    total_hotspots_detected: int = Field(..., description="Total clustered hotspots found")
    total_clustered_crimes: int = Field(..., description="Number of crimes belonging to hotspots")
    total_noise_crimes: int = Field(..., description="Number of outlier crimes not part of any hotspot")
    top_hotspot_district: Optional[str] = Field(None, description="District with the highest density of crimes")
    average_hotspot_radius_meters: float = Field(..., description="Average radius of all detected hotspots")
    highest_risk_hotspot_id: Optional[int] = Field(None, description="Cluster ID with the highest crime count/risk")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_crimes_analyzed": 1500,
                "total_hotspots_detected": 12,
                "total_clustered_crimes": 850,
                "total_noise_crimes": 650,
                "top_hotspot_district": "Bengaluru Urban",
                "average_hotspot_radius_meters": 420.2,
                "highest_risk_hotspot_id": 2
            }
        }
    }
