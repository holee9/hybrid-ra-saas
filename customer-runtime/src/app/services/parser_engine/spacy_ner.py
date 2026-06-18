"""Stage 2: spaCy NER extraction (lazy import, injectable model loader).

B1 compliance: spaCy is imported lazily inside default_model_loader().
When spaCy is absent or the loader raises, extract() returns {} gracefully.

Singleton pattern: get_nlp() reads the model pre-loaded in app.state at lifespan.
Falls back to default_model_loader() if app.state is unavailable (e.g. unit tests).
"""
import logging
from typing import Any, Callable

from fastapi import Request

from app.schemas.parse import ExtractionStage, FieldExtraction
from app.services.parser_engine.confidence import calculate

logger = logging.getLogger(__name__)

# Log spaCy absence once, not per call
_SPACY_MISSING_LOGGED = False

# NER label → field name mapping (heuristic)
_NER_LABEL_TO_FIELD: dict[str, str] = {
    "PRODUCT": "device_name",
    "ORG": "device_classification",
    "GPE": "region_targets",
    "LOC": "region_targets",
    "CARDINAL": "maintenance_interval",
    "DATE": "maintenance_interval",
}


def default_model_loader() -> Any:
    """Load spaCy en_core_web_sm model (lazy import).

    Raises:
        ImportError: If spaCy is not installed.
        RuntimeError: If the model is not downloaded.
    """
    import spacy  # noqa: PLC0415  # lazy import (B1)
    return spacy.load("en_core_web_sm")


def get_nlp(request: Request) -> Any | None:
    """FastAPI dependency: return the singleton spaCy model from app.state.

    Falls back to default_model_loader() when app.state.spacy_model is not set
    (e.g. during unit tests that construct a bare Request without lifespan).
    Returns None if spaCy is unavailable — callers must handle None gracefully.
    """
    model = getattr(request.app.state, "spacy_model", None)
    if model is not None:
        return model
    # Fallback for test contexts without lifespan
    try:
        return default_model_loader()
    except (ImportError, OSError):
        return None


def extract(
    text: str,
    fields_needed: list[str],
    *,
    model_loader: Callable[[], Any] | None = None,
) -> dict[str, FieldExtraction]:
    """Extract fields using spaCy NER.

    Args:
        text: Document plain text.
        fields_needed: Field names to attempt extraction for.
        model_loader: Callable that returns a spaCy model.
                      Defaults to default_model_loader.
                      Inject a fake for unit testing (B1).

    Returns:
        Dict of extracted fields, or {} if loader fails (graceful degrade).
    """
    global _SPACY_MISSING_LOGGED

    if not fields_needed:
        return {}

    loader = model_loader if model_loader is not None else default_model_loader

    try:
        nlp = loader()
    except (ImportError, RuntimeError, Exception) as exc:
        if not _SPACY_MISSING_LOGGED:
            logger.warning("spaCy NER unavailable, skipping stage 2: %s", exc)
            _SPACY_MISSING_LOGGED = True
        return {}

    try:
        doc = nlp(text)
    except Exception as exc:
        logger.warning("spaCy inference failed: %s", exc)
        return {}

    # Aggregate entities by mapped field
    field_values: dict[str, list[str]] = {f: [] for f in fields_needed}
    for ent in doc.ents:
        mapped_field = _NER_LABEL_TO_FIELD.get(ent.label_)
        if mapped_field and mapped_field in field_values:
            field_values[mapped_field].append(ent.text)

    result: dict[str, FieldExtraction] = {}
    for field in fields_needed:
        values = field_values.get(field, [])
        if values:
            value = values[0] if len(values) == 1 else values
            field_completeness = 1.0
            rule_match = 0.6  # NER is less precise than rule-based
        else:
            value = None
            field_completeness = 0.0
            rule_match = 0.0

        confidence = calculate(
            field_completeness=field_completeness,
            rule_match=rule_match,
            semantic_similarity=0.0,
        )
        result[field] = FieldExtraction(
            value=value,
            confidence=confidence,
            stage=ExtractionStage.NER,
        )

    return result
