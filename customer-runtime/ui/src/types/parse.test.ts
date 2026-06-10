import { describe, it, expect } from "vitest";
import {
  ExtractionStage,
  IFU_FIELD_NAMES,
  isIfuFieldName,
  isFieldExtraction,
  isParsedFields,
} from "./parse";

describe("IFU_FIELD_NAMES", () => {
  it("has exactly 15 fields", () => {
    expect(IFU_FIELD_NAMES.length).toBe(15);
  });

  it("contains device_name", () => {
    expect(IFU_FIELD_NAMES).toContain("device_name");
  });

  it("contains all required fields", () => {
    const required = [
      "device_name",
      "intended_use",
      "indications",
      "contraindications",
      "warnings",
      "device_classification",
      "region_targets",
      "cybersecurity_requirements",
      "precautions",
      "product_code",
      "maintenance_interval",
      "cleaning_disinfection",
      "software_version",
      "accessories",
      "disposal_instructions",
    ];
    required.forEach((f) => expect(IFU_FIELD_NAMES).toContain(f));
  });
});

describe("isIfuFieldName", () => {
  it("returns true for valid field names", () => {
    expect(isIfuFieldName("device_name")).toBe(true);
    expect(isIfuFieldName("disposal_instructions")).toBe(true);
  });

  it("returns false for invalid field names", () => {
    expect(isIfuFieldName("unknown_field")).toBe(false);
    expect(isIfuFieldName("")).toBe(false);
    expect(isIfuFieldName("DEVICE_NAME")).toBe(false);
  });
});

describe("isFieldExtraction", () => {
  it("returns true for valid FieldExtraction", () => {
    expect(
      isFieldExtraction({
        value: "test",
        confidence: 0.9,
        stage: ExtractionStage.RULE,
        needs_correction: false,
      })
    ).toBe(true);
  });

  it("returns true for null value", () => {
    expect(
      isFieldExtraction({
        value: null,
        confidence: 0.0,
        stage: ExtractionStage.NONE,
        needs_correction: true,
      })
    ).toBe(true);
  });

  it("returns true for array value", () => {
    expect(
      isFieldExtraction({
        value: ["item1", "item2"],
        confidence: 0.75,
        stage: ExtractionStage.NER,
        needs_correction: false,
      })
    ).toBe(true);
  });

  it("returns false for missing confidence", () => {
    expect(isFieldExtraction({ stage: "rule_based", needs_correction: false })).toBe(
      false
    );
  });

  it("returns false for null/undefined", () => {
    expect(isFieldExtraction(null)).toBe(false);
    expect(isFieldExtraction(undefined)).toBe(false);
    expect(isFieldExtraction("string")).toBe(false);
  });
});

describe("isParsedFields", () => {
  const makeField = (overrides = {}) => ({
    value: null,
    confidence: 0.5,
    stage: "rule_based",
    needs_correction: false,
    ...overrides,
  });

  const makeValid = () => {
    const obj: Record<string, unknown> = {
      overall_confidence: 0.8,
      requires_correction: false,
      rejected: false,
    };
    IFU_FIELD_NAMES.forEach((f) => {
      obj[f] = makeField();
    });
    return obj;
  };

  it("returns true for valid ParsedFields", () => {
    expect(isParsedFields(makeValid())).toBe(true);
  });

  it("returns false for missing overall_confidence", () => {
    const v = makeValid();
    delete (v as Record<string, unknown>)["overall_confidence"];
    expect(isParsedFields(v)).toBe(false);
  });

  it("returns false for missing field", () => {
    const v = makeValid();
    delete (v as Record<string, unknown>)["device_name"];
    expect(isParsedFields(v)).toBe(false);
  });

  it("returns false for null", () => {
    expect(isParsedFields(null)).toBe(false);
  });
});

describe("ExtractionStage enum", () => {
  it("has correct string values", () => {
    expect(ExtractionStage.RULE).toBe("rule_based");
    expect(ExtractionStage.NER).toBe("spacy_ner");
    expect(ExtractionStage.LLM).toBe("llm_fallback");
    expect(ExtractionStage.NONE).toBe("none");
  });
});
