from typing import List, Tuple, Optional

class ExplainabilityBuilder:
    """Standalone engine to assemble bullet reason lists and unified summary strings."""

    @staticmethod
    def build(
        semantic_sim: float,
        fts_score: float,
        mo_score: Optional[float],
        matched_features: List[str],
        missing_features: List[str],
        matched_terms: List[str],
    ) -> Tuple[List[str], str]:
        """
        Build (explanations_list, explanation_str) from scoring diagnostics.
        """
        explanations_list = []
        
        # 1. Semantic Match reason
        if semantic_sim >= 0.85:
            explanations_list.append(f"✓ Very high narrative similarity ({round(semantic_sim * 100, 1)}%)")
        elif semantic_sim >= 0.70:
            explanations_list.append(f"✓ Strong narrative similarity ({round(semantic_sim * 100, 1)}%)")
        elif semantic_sim >= 0.50:
            explanations_list.append(f"✓ Partial narrative similarity ({round(semantic_sim * 100, 1)}%)")

        # 2. FTS Match reason
        if matched_terms:
            explanations_list.append(f"✓ Exact keyword match: {', '.join(matched_terms)}")
        elif fts_score > 0:
            explanations_list.append("✓ Keyword matched in related fields")

        # 3. MO Feature Alignment reasons
        if mo_score is not None:
            readable = {
                "crime_type":        "Crime Category",
                "crime_method":     "Crime Method",
                "weapon_used":      "Weapon",
                "entry_method":     "Entry Method",
                "target_type":      "Target",
                "escape_method":    "Escape Method",
                "time_of_day_slot": "Time Slot",
                "gang_involved":    "Gang Indicator",
                "district":         "District",
            }
            for f in matched_features:
                explanations_list.append(f"✓ {readable.get(f, f)} matched")
            for f in missing_features:
                explanations_list.append(f"✗ missing {readable.get(f, f)}")

        explanation_str = ". ".join(explanations_list) if explanations_list else "Matches baseline similarity filters."
        return explanations_list, explanation_str
