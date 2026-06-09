"""Confidence score calculation for field extractions.

Formula:
    score = 0.50 * field_completeness + 0.30 * rule_match + 0.20 * semantic_similarity

Thresholds are env-overridable for deployment tuning.
"""
import os

# @MX:ANCHOR: [AUTO] calculate() — confidence formula entry point, fan_in >= 3
# @MX:REASON: Called by rule_based, spacy_ner, llm_fallback stages and overall()
CORRECTION_UI_THRESHOLD: float = float(
    os.environ.get("PARSER_CORRECTION_THRESHOLD", "0.85")
)
REJECT_THRESHOLD: float = float(
    os.environ.get("PARSER_REJECT_THRESHOLD", "0.50")
)

# Weights for the confidence formula
_FIELD_COMPLETENESS_WEIGHT: float = 0.50
_RULE_MATCH_WEIGHT: float = 0.30
_SEMANTIC_SIMILARITY_WEIGHT: float = 0.20

# Required fields for overall_confidence calculation
_REQUIRED_FIELDS: tuple[str, ...] = (
    "device_name",
    "intended_use",
    "indications",
    "contraindications",
    "warnings",
    "device_classification",
    "region_targets",
    "cybersecurity_requirements",
)


def calculate(
    field_completeness: float,
    rule_match: float,
    semantic_similarity: float,
) -> float:
    """Return weighted confidence score in [0.0, 1.0].

    Args:
        field_completeness: Ratio of non-None fields extracted.
        rule_match: Score from regex/keyword matching stage.
        semantic_similarity: Semantic embedding similarity score.

    Returns:
        Weighted confidence in [0.0, 1.0].
    """
    return (
        _FIELD_COMPLETENESS_WEIGHT * field_completeness
        + _RULE_MATCH_WEIGHT * rule_match
        + _SEMANTIC_SIMILARITY_WEIGHT * semantic_similarity
    )


def overall(parsed_fields: "ParsedFields") -> float:  # type: ignore[name-defined]  # noqa: F821
    """Compute overall_confidence as average over required fields.

    Args:
        parsed_fields: Completed ParsedFields instance.

    Returns:
        Mean confidence across the 8 required IFU fields.
    """
    scores = [
        getattr(parsed_fields, field).confidence
        for field in _REQUIRED_FIELDS
    ]
    return sum(scores) / len(scores) if scores else 0.0
