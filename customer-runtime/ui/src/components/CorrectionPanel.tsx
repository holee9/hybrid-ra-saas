import { useEffect } from "react";
import { useBlocker } from "react-router-dom";
import { ParsedFields, IFU_FIELD_NAMES, IfuFieldName } from "../types/parse";
import { useCorrections } from "../hooks/useCorrections";
import { useToast } from "../lib/toast";
import { FieldRow } from "./FieldRow";
import { RejectedBanner } from "./RejectedBanner";
import { ApiError } from "../lib/api";

interface CorrectionPanelProps {
  jobId: string;
  initialFields: ParsedFields;
}

// @MX:ANCHOR: [AUTO] CorrectionPanel — main UI orchestrator for IFU correction workflow
// @MX:REASON: Integrates useCorrections + useToast + FieldRow + RejectedBanner (fan_in >= 3)
export function CorrectionPanel({ jobId, initialFields }: CorrectionPanelProps) {
  const { fields, dirtyFields, updateField, save, saving, undo } = useCorrections(
    jobId,
    initialFields
  );
  const { showToast } = useToast();

  const isDirty = dirtyFields.size > 0;
  const isRejected = fields.rejected;
  const isDisabled = isRejected || saving;
  const canSave = isDirty && !isDisabled;

  // Warn on browser tab close / refresh when there are unsaved changes
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  // Warn on in-app navigation away from unsaved changes
  const blocker = useBlocker(isDirty && !saving);
  useEffect(() => {
    if (blocker.state === "blocked") {
      const confirmed = window.confirm("저장하지 않은 변경 사항이 있습니다. 나가시겠습니까?");
      if (confirmed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker]);

  async function handleSave() {
    try {
      await save();
      showToast("저장되었습니다.", "success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          showToast("검증 실패: 입력값을 확인해주세요.", "error");
        } else if (err.status === 401) {
          showToast("인증 실패", "error");
        } else {
          showToast(`저장 실패: ${err.message}`, "error");
        }
      } else {
        showToast("네트워크 오류. 재시도해주세요.", "error");
      }
    }
  }

  const confidencePct = Math.round(fields.overall_confidence * 100);

  return (
    <div className="flex flex-col gap-4">
      {isRejected && <RejectedBanner />}

      {/* Overall confidence progress */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-600 w-28 shrink-0">전체 신뢰도</span>
        <div
          role="progressbar"
          aria-valuenow={confidencePct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="전체 신뢰도"
          className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden"
        >
          <div
            className={`h-full rounded-full transition-all ${
              confidencePct >= 85
                ? "bg-green-500"
                : confidencePct >= 75
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-gray-700 w-10 text-right">
          {confidencePct}%
        </span>
      </div>

      {/* 15 field rows */}
      <div className="flex flex-col gap-1">
        {IFU_FIELD_NAMES.map((fieldName) => (
          <FieldRow
            key={fieldName}
            fieldName={fieldName as IfuFieldName}
            extraction={fields[fieldName as IfuFieldName]}
            isDirty={dirtyFields.has(fieldName as IfuFieldName)}
            disabled={isDisabled}
            onUpdate={(val) => updateField(fieldName as IfuFieldName, val)}
          />
        ))}
      </div>

      {/* Save button */}
      <div className="flex justify-end gap-3 pt-2 border-t">
        {isDirty && !saving && (
          <button
            type="button"
            onClick={() => {
              dirtyFields.forEach((f) => undo(f));
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 underline"
          >
            모두 되돌리기
          </button>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={!canSave}
          aria-label="저장"
          className="px-6 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "저장 중..." : "저장"}
        </button>
      </div>
    </div>
  );
}
