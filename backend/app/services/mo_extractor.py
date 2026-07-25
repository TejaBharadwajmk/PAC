import os
import json
import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class MOExtractorService:
    """Configurable synonym-driven Feature Extraction Service."""

    def __init__(self) -> None:
        self.mappings: Dict[str, Dict[str, List[str]]] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load synonym mapping JSON file from backend configuration directory."""
        config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mapping_path = os.path.join(config_dir, "config", "mo_mappings.json")
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                self.mappings = json.load(f)
            logger.info("Successfully loaded MO synonym mappings from mo_mappings.json.")
        except Exception as e:
            logger.error(f"Failed to load MO synonym mappings: {e}")
            self.mappings = {}

    def extract_query_features(
        self,
        query_text: str,
    ) -> Tuple[Dict[str, str], float, List[str], List[str]]:
        """
        Scan query_text against mappings to extract structured MO features.

        Returns:
            (query_features, confidence, matched_keywords, unknown_tokens)
        """
        if not query_text or not query_text.strip():
            return {}, 0.0, [], []

        query_lower = query_text.lower()
        # Find all alphanumeric tokens
        tokens = re.findall(r'\w+', query_lower)
        
        query_features: Dict[str, str] = {}
        matched_keywords: List[str] = []
        matched_tokens: List[str] = []

        # Scan each category in mappings
        for category, subcategories in self.mappings.items():
            for key, synonyms in subcategories.items():
                if category in query_features:
                    break
                for syn in synonyms:
                    # Look for exact word boundary matches to avoid partial keyword overlaps
                    pattern = r'(?<!\w)' + re.escape(syn.lower()) + r'(?!\w)'
                    if re.search(pattern, query_lower):
                        query_features[category] = key
                        matched_keywords.append(syn)
                        # Mark matched tokens to identify unknowns
                        matched_tokens.extend(re.findall(r'\w+', syn.lower()))
                        break # match found for this key, proceed to next category

        # Identify unknown tokens (alphanumeric words > 3 characters not matching synonyms)
        unknown_tokens: List[str] = []
        for t in tokens:
            if len(t) > 3 and t not in matched_tokens:
                # Basic check if it's not a common stopword
                stopwords = {"with", "that", "this", "from", "their", "after", "they", "were", "using"}
                if t not in stopwords:
                    unknown_tokens.append(t)

        # Confidence is calculated as matched categories relative to possible scanned categories
        total_categories = len(self.mappings)
        confidence = round(len(query_features) / total_categories, 2) if total_categories > 0 else 0.0

        return query_features, confidence, sorted(list(set(matched_keywords))), sorted(list(set(unknown_tokens)))

# Export a singleton instance for shared import
mo_extractor = MOExtractorService()
