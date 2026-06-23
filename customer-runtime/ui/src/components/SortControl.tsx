// SPEC-UI-002: Sort field and direction controls
import type { SortField, SortOrder } from "../types/jobs";

interface Props {
  field: SortField;
  order: SortOrder;
  onChange: (field: SortField, order: SortOrder) => void;
}

const FIELD_LABELS: Record<SortField, string> = {
  created_at: "작성일",
  overall_confidence: "신뢰도",
};

export function SortControl({ field, order, onChange }: Props): JSX.Element {
  const toggleOrder = () => onChange(field, order === "desc" ? "asc" : "desc");
  const toggleField = (newField: SortField) => {
    if (newField === field) {
      toggleOrder();
    } else {
      onChange(newField, "desc");
    }
  };

  return (
    <div
      role="group"
      aria-label="정렬 기준"
      className="flex items-center gap-2 text-sm text-gray-600 mb-3"
    >
      <span id="sort-label">정렬:</span>
      {(Object.keys(FIELD_LABELS) as SortField[]).map((f) => {
        const isActive = field === f;
        const directionLabel = isActive
          ? order === "desc" ? "내림차순" : "오름차순"
          : "내림차순";
        return (
          <button
            key={f}
            onClick={() => toggleField(f)}
            aria-pressed={isActive}
            aria-label={`${FIELD_LABELS[f]} 기준 정렬${isActive ? `, ${directionLabel}` : ""}`}
            className={`px-2 py-1 rounded border text-xs ${
              isActive
                ? "border-blue-500 text-blue-600 font-medium"
                : "border-gray-300 hover:border-gray-400"
            }`}
          >
            {FIELD_LABELS[f]} {isActive ? (order === "desc" ? "▼" : "▲") : ""}
          </button>
        );
      })}
    </div>
  );
}
