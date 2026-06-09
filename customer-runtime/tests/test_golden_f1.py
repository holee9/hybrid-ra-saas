"""T-011: Golden dataset F1 테스트 (integration, requires golden fixtures + spaCy + Ollama)."""
import pathlib
import pytest


GOLDEN_DIR = pathlib.Path(__file__).parent / "fixtures" / "parser" / "golden"

skip_no_golden = pytest.mark.skipif(
    not list(GOLDEN_DIR.glob("*.docx")),
    reason="Golden dataset not available — provide .docx files in tests/fixtures/parser/golden/",
)


@skip_no_golden
@pytest.mark.integration
def test_golden_f1_macro_score(skip_no_spacy, skip_no_ollama):
    """Macro-F1 across golden dataset must be >= 0.85.

    Dataset format: each golden/*.docx has a matching *.json with expected field values.
    """
    import json
    import asyncio
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import IFU_FIELD_NAMES

    engine = ParserEngine()
    golden_files = list(GOLDEN_DIR.glob("*.docx"))
    assert golden_files, "No golden .docx files found"

    all_precisions: list[float] = []
    all_recalls: list[float] = []

    async def run_one(docx_path: pathlib.Path):
        label_path = docx_path.with_suffix(".json")
        if not label_path.exists():
            return None

        with open(docx_path, "rb") as f:
            docx_bytes = f.read()
        with open(label_path, encoding="utf-8") as f:
            expected = json.load(f)

        parsed = await engine.parse(docx_bytes, "docx")

        tp = fp = fn = 0
        for field in IFU_FIELD_NAMES:
            fe = getattr(parsed, field)
            expected_val = expected.get(field)
            predicted_val = fe.value

            if expected_val and predicted_val:
                if expected_val.lower().strip() in str(predicted_val).lower():
                    tp += 1
                else:
                    fp += 1
                    fn += 1
            elif expected_val and not predicted_val:
                fn += 1
            elif not expected_val and predicted_val:
                fp += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return precision, recall

    for docx_path in golden_files:
        result = asyncio.get_event_loop().run_until_complete(run_one(docx_path))
        if result is not None:
            p, r = result
            all_precisions.append(p)
            all_recalls.append(r)

    if not all_precisions:
        pytest.skip("No matched golden files with labels")

    macro_p = sum(all_precisions) / len(all_precisions)
    macro_r = sum(all_recalls) / len(all_recalls)
    f1 = 2 * macro_p * macro_r / (macro_p + macro_r) if (macro_p + macro_r) > 0 else 0.0

    assert f1 >= 0.85, f"Macro-F1 {f1:.3f} < 0.85 threshold"
