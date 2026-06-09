// @MX:ANCHOR: [AUTO] IFU_FIELD_NAMES — canonical 15-field list, single source of truth
// @MX:REASON: Referenced by FieldRow labels, useCorrections whitelist, CorrectionPanel, ConfidenceBadge

export enum ExtractionStage {
  RULE = "rule_based",
  NER = "spacy_ner",
  LLM = "llm_fallback",
  NONE = "none",
}

export interface FieldExtraction {
  value: string | string[] | null;
  confidence: number;
  stage: ExtractionStage;
  needs_correction: boolean;
}

// @MX:ANCHOR: [AUTO] IFU field names tuple — const assertion ensures exhaustive type
// @MX:REASON: Used as Partial<Record<IfuFieldName, ...>> key constraint in CorrectionRequest
export const IFU_FIELD_NAMES = [
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
] as const;

export type IfuFieldName = (typeof IFU_FIELD_NAMES)[number];

export interface ParsedFields {
  device_name: FieldExtraction;
  intended_use: FieldExtraction;
  indications: FieldExtraction;
  contraindications: FieldExtraction;
  warnings: FieldExtraction;
  device_classification: FieldExtraction;
  region_targets: FieldExtraction;
  cybersecurity_requirements: FieldExtraction;
  precautions: FieldExtraction;
  product_code: FieldExtraction;
  maintenance_interval: FieldExtraction;
  cleaning_disinfection: FieldExtraction;
  software_version: FieldExtraction;
  accessories: FieldExtraction;
  disposal_instructions: FieldExtraction;
  overall_confidence: number;
  requires_correction: boolean;
  rejected: boolean;
}

export interface ParseJobResponse {
  job_id: string;
  status: string;
  parsed_fields?: ParsedFields | null;
}

// PATCH body — array values must be joined with \n before sending
// @MX:NOTE: [AUTO] Backend CorrectionsRequest.corrections is dict[str, str] — no arrays
export interface CorrectionRequest {
  corrections: Partial<Record<IfuFieldName, string>>;
}

// Type guards
export function isIfuFieldName(key: string): key is IfuFieldName {
  return (IFU_FIELD_NAMES as readonly string[]).includes(key);
}

export function isFieldExtraction(v: unknown): v is FieldExtraction {
  if (!v || typeof v !== "object") return false;
  const obj = v as Record<string, unknown>;
  return (
    typeof obj["confidence"] === "number" &&
    typeof obj["stage"] === "string" &&
    typeof obj["needs_correction"] === "boolean"
  );
}

export function isParsedFields(v: unknown): v is ParsedFields {
  if (!v || typeof v !== "object") return false;
  const obj = v as Record<string, unknown>;
  return (
    typeof obj["overall_confidence"] === "number" &&
    typeof obj["requires_correction"] === "boolean" &&
    typeof obj["rejected"] === "boolean" &&
    IFU_FIELD_NAMES.every((f) => isFieldExtraction(obj[f]))
  );
}
