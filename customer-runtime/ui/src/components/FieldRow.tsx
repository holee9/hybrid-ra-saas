import { useState } from "react";
import { FieldExtraction, IfuFieldName } from "../types/parse";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { StageIndicator } from "./StageIndicator";

// @MX:ANCHOR: [AUTO] IFU field label map — Korean display names for all 15 fields
// @MX:REASON: Referenced by FieldRow render and potentially future i18n layer (fan_in >= 3)
const FIELD_LABELS: Record<IfuFieldName, string> = {
  device_name: "기기명",
  intended_use: "사용 목적",
  indications: "적응증",
  contraindications: "금기사항",
  warnings: "경고",
  device_classification: "기기 분류",
  region_targets: "대상 지역",
  cybersecurity_requirements: "사이버보안 요구사항",
  precautions: "주의사항",
  product_code: "제품 코드",
  maintenance_interval: "유지보수 주기",
  cleaning_disinfection: "세척/소독",
  software_version: "소프트웨어 버전",
  accessories: "부속품",
  disposal_instructions: "폐기 지침",
};

interface FieldRowProps {
  fieldName: IfuFieldName;
  extraction: FieldExtraction;
  isDirty: boolean;
  disabled: boolean;
  onUpdate: (value: string) => void;
}

function displayValue(value: string | string[] | null): string {
  if (value === null || value === undefined) return "(없음)";
  if (Array.isArray(value)) return value.join("\n");
  return value;
}

export function FieldRow({
  fieldName,
  extraction,
  isDirty,
  disabled,
  onUpdate,
}: FieldRowProps) {
  const [editing, setEditing] = useState(false);
  const currentDisplay = displayValue(extraction.value);

  function handleClick() {
    if (!disabled) setEditing(true);
  }

  function handleBlur() {
    setEditing(false);
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    onUpdate(e.target.value);
  }

  const borderClass = isDirty
    ? "border-l-4 border-l-yellow-400"
    : "border-l-4 border-l-transparent";

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-md bg-white hover:bg-gray-50 ${borderClass}`}
    >
      <div className="w-40 shrink-0">
        <span className="text-sm font-medium text-gray-700">
          {FIELD_LABELS[fieldName]}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        {editing ? (
          <textarea
            className="w-full text-sm border border-blue-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y min-h-[3rem]"
            value={currentDisplay === "(없음)" ? "" : currentDisplay}
            onChange={handleChange}
            onBlur={handleBlur}
            autoFocus
          />
        ) : (
          <span
            role={disabled ? undefined : "button"}
            tabIndex={disabled ? undefined : 0}
            aria-label={disabled ? undefined : `${FIELD_LABELS[fieldName]} 편집`}
            className={`text-sm text-gray-800 whitespace-pre-wrap ${disabled ? "cursor-default" : "cursor-pointer hover:bg-blue-50 rounded px-1 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:rounded"}`}
            onClick={handleClick}
            onKeyDown={disabled ? undefined : (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleClick();
              }
            }}
          >
            {currentDisplay}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <ConfidenceBadge
          confidence={extraction.confidence}
          needs_correction={extraction.needs_correction}
        />
        <StageIndicator stage={extraction.stage} />
      </div>
    </div>
  );
}
