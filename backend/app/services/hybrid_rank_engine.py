"""
PAC — HybridRankEngine (Phase 3 / Phase 5)

A completely signal-agnostic score normalization, weight redistribution,
and rank fusion engine.

Design principles:
  • Accepts a generic list of RankingSignal objects — no hardcoded knowledge
    of "semantic", "fts", or "mo" signal types.
  • Future signals (Geo distance, Neo4j graph centrality, recency decay, etc.)
    can be added by creating a new RankingSignal and appending it to the list;
    no changes to this module are required.
  • Per-request weight overrides (Phase 5) are passed in as RankingSignal.weight
    values by the caller (SimilarityService) — HybridRankEngine does not read
    settings directly.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class RankingSignal:
    """
    A single scoring signal that contributes to the final hybrid rank.

    Attributes:
        name:   Human-readable identifier (e.g. "semantic", "fts", "mo").
        value:  Normalised score in [0.0, 1.0].
        weight: Configured importance weight (before redistribution).
        active: If False the signal is excluded from fusion (weight set to 0).
    """
    name: str
    value: float
    weight: float
    active: bool = True


@dataclass
class FusionResult:
    """
    Output of HybridRankEngine.fuse().

    Attributes:
        score:               Final blended score in [0.0, 1.0].
        normalized_weights:  Per-signal weight after redistribution (sums to 1.0).
        configured_weights:  Per-signal weight as supplied by the caller.
        active_signals:      Names of signals that were included in fusion.
    """
    score: float
    normalized_weights: Dict[str, float]
    configured_weights: Dict[str, float]
    active_signals: List[str]


class HybridRankEngine:
    """
    Signal-agnostic hybrid rank fusion engine.

    Usage::

        signals = [
            RankingSignal(name="semantic", value=0.82, weight=0.60, active=True),
            RankingSignal(name="fts",      value=0.55, weight=0.25, active=True),
            RankingSignal(name="mo",       value=0.70, weight=0.15, active=False),
        ]
        result = HybridRankEngine.fuse(signals)
        # result.score             → 0.7... (semantic+fts only, renormalized)
        # result.active_signals    → ["semantic", "fts"]
        # result.normalized_weights → {"semantic": 0.706, "fts": 0.294}
    """

    @staticmethod
    def fuse(signals: List[RankingSignal]) -> FusionResult:
        """
        Normalize active signal weights and compute a blended score.

        Steps:
          1. Filter to active signals only.
          2. Sum active weights; if zero fall back to equal distribution.
          3. Compute per-signal normalized weight = weight / total_active_weight.
          4. Compute fused score = Σ(value × normalized_weight).

        Args:
            signals: Ordered list of RankingSignal instances.

        Returns:
            FusionResult with score, weights, and diagnostics.
        """
        configured_weights: Dict[str, float] = {s.name: s.weight for s in signals}

        active = [s for s in signals if s.active]

        if not active:
            # Nothing active — return neutral score
            return FusionResult(
                score=0.0,
                normalized_weights={},
                configured_weights=configured_weights,
                active_signals=[],
            )

        total_weight = sum(s.weight for s in active)

        if total_weight <= 0.0:
            # All active weights are zero — distribute equally
            equal_w = 1.0 / len(active)
            normalized_weights = {s.name: round(equal_w, 6) for s in active}
        else:
            normalized_weights = {
                s.name: round(s.weight / total_weight, 6) for s in active
            }

        fused_score = sum(
            s.value * normalized_weights[s.name] for s in active
        )

        return FusionResult(
            score=round(fused_score, 4),
            normalized_weights=normalized_weights,
            configured_weights=configured_weights,
            active_signals=[s.name for s in active],
        )
