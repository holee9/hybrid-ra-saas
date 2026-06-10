import { ExtractionStage } from "../types/parse";

interface StageIndicatorProps {
  stage: ExtractionStage;
}

// @MX:NOTE: [AUTO] Stage label map — mirrors Python ExtractionStage enum values
const STAGE_LABELS: Record<ExtractionStage, string> = {
  [ExtractionStage.RULE]: "규칙 기반",
  [ExtractionStage.NER]: "NER",
  [ExtractionStage.LLM]: "LLM",
  [ExtractionStage.NONE]: "수동",
};

const STAGE_STYLES: Record<ExtractionStage, string> = {
  [ExtractionStage.RULE]: "bg-blue-100 text-blue-700",
  [ExtractionStage.NER]: "bg-purple-100 text-purple-700",
  [ExtractionStage.LLM]: "bg-orange-100 text-orange-700",
  [ExtractionStage.NONE]: "bg-gray-100 text-gray-600",
};

export function StageIndicator({ stage }: StageIndicatorProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STAGE_STYLES[stage]}`}
    >
      {STAGE_LABELS[stage]}
    </span>
  );
}
