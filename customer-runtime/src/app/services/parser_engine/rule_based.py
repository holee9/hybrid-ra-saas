"""Stage 1: regex + keyword dictionary extraction (EN/KO).

All extraction is CPU-only regex/string operations. No network, no GPU.
"""
import re

from app.schemas.parse import ExtractionStage, FieldExtraction
from app.services.parser_engine.confidence import calculate

# Compiled regex patterns per field — EN patterns
_EN_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    field: [] for field in (
        "device_name", "intended_use", "indications", "contraindications",
        "warnings", "device_classification", "region_targets",
        "cybersecurity_requirements", "precautions", "product_code",
        "maintenance_interval", "cleaning_disinfection", "software_version",
        "accessories", "disposal_instructions",
    )
}

# EN keyword → field mapping (label: regex pattern to capture value)
_EN_LABEL_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "device_name": [
        ("en", re.compile(r"(?:Device\s+Name|Product\s+Name)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "intended_use": [
        ("en", re.compile(r"(?:Intended\s+Use|Intended\s+Purpose)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "indications": [
        ("en", re.compile(r"(?:Indications?(?:\s+for\s+use)?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "contraindications": [
        ("en", re.compile(r"(?:Contra-?indications?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "warnings": [
        ("en", re.compile(r"(?:Warning[s]?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "device_classification": [
        ("en", re.compile(r"(?:Device\s+Classification|Classification)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "region_targets": [
        ("en", re.compile(r"(?:Region[s]?\s+Target[s]?|Target\s+Region[s]?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "cybersecurity_requirements": [
        ("en", re.compile(r"(?:Cybersecurity\s+Requirements?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "precautions": [
        ("en", re.compile(r"(?:Precautions?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "product_code": [
        ("en", re.compile(r"(?:Product\s+Code|Item\s+Code|SKU)\s*[:：]\s*(\S+)", re.IGNORECASE)),
    ],
    "maintenance_interval": [
        ("en", re.compile(r"(?:Maintenance\s+Interval)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "cleaning_disinfection": [
        ("en", re.compile(r"(?:Cleaning\s+(?:and\s+)?Disinfection|Disinfection)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "software_version": [
        ("en", re.compile(r"(?:Software\s+Version|SW\s+Version|Version)\s*[:：]\s*(\S+)", re.IGNORECASE)),
    ],
    "accessories": [
        ("en", re.compile(r"(?:Accessories)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
    "disposal_instructions": [
        ("en", re.compile(r"(?:Disposal\s+Instructions?)\s*[:：]\s*(.+)", re.IGNORECASE)),
    ],
}

# KO label patterns
_KO_LABEL_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "device_name": [
        ("ko", re.compile(r"(?:제품명|장치명|기기명)\s*[:：]\s*(.+)")),
    ],
    "intended_use": [
        ("ko", re.compile(r"(?:사용목적|사용\s*목적|의도된\s*사용)\s*[:：]\s*(.+)")),
    ],
    "indications": [
        ("ko", re.compile(r"(?:적응증|적응\s*증)\s*[:：]\s*(.+)")),
    ],
    "contraindications": [
        ("ko", re.compile(r"(?:금기사항|금기\s*사항)\s*[:：]\s*(.+)")),
    ],
    "warnings": [
        ("ko", re.compile(r"(?:경고|경고\s*사항|주의\s*경고)\s*[:：]\s*(.+)")),
    ],
    "device_classification": [
        ("ko", re.compile(r"(?:제품\s*분류|장치\s*분류|등급)\s*[:：]\s*(.+)")),
    ],
    "region_targets": [
        ("ko", re.compile(r"(?:지역\s*대상|대상\s*지역|판매\s*지역)\s*[:：]\s*(.+)")),
    ],
    "cybersecurity_requirements": [
        ("ko", re.compile(r"(?:사이버보안\s*요구사항|사이버\s*보안)\s*[:：]\s*(.+)")),
    ],
    "precautions": [
        ("ko", re.compile(r"(?:주의사항|주의\s*사항|예방\s*조치)\s*[:：]\s*(.+)")),
    ],
    "product_code": [
        ("ko", re.compile(r"(?:제품\s*코드|품목\s*번호|모델\s*번호)\s*[:：]\s*(\S+)")),
    ],
    "maintenance_interval": [
        ("ko", re.compile(r"(?:유지보수\s*주기|정비\s*주기)\s*[:：]\s*(.+)")),
    ],
    "cleaning_disinfection": [
        ("ko", re.compile(r"(?:세척\s*(?:및\s*)?소독|소독\s*방법|청소\s*방법)\s*[:：]\s*(.+)")),
    ],
    "software_version": [
        ("ko", re.compile(r"(?:소프트웨어\s*버전|SW\s*버전|버전)\s*[:：]\s*(\S+)")),
    ],
    "accessories": [
        ("ko", re.compile(r"(?:부속품|액세서리|구성품)\s*[:：]\s*(.+)")),
    ],
    "disposal_instructions": [
        ("ko", re.compile(r"(?:폐기\s*지침|폐기\s*방법|처분\s*방법)\s*[:：]\s*(.+)")),
    ],
}


def _extract_field(text: str, field: str) -> tuple[str | None, float]:
    """Try to extract a single field using EN and KO patterns.

    Returns:
        (value, match_score) where match_score is 0.0 or 1.0.
    """
    all_patterns = (
        _EN_LABEL_PATTERNS.get(field, [])
        + _KO_LABEL_PATTERNS.get(field, [])
    )
    for _lang, pattern in all_patterns:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value, 1.0
    return None, 0.0


def extract(text: str, fields_needed: list[str]) -> dict[str, FieldExtraction]:
    """Extract specified fields from text using rule-based patterns.

    Pure function: no network, no GPU, no external state.

    Args:
        text: Document plain text.
        fields_needed: List of field names to extract.

    Returns:
        Dict mapping field name → FieldExtraction with stage=RULE.
    """
    result: dict[str, FieldExtraction] = {}

    for field in fields_needed:
        value, match_score = _extract_field(text, field)
        field_completeness = 1.0 if value is not None else 0.0
        confidence = calculate(
            field_completeness=field_completeness,
            rule_match=match_score,
            semantic_similarity=0.0,  # no embeddings in stage 1
        )
        result[field] = FieldExtraction(
            value=value,
            confidence=confidence,
            stage=ExtractionStage.RULE,
        )

    return result
