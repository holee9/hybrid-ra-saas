import { useState, useCallback, useRef } from "react";
import {
  ParsedFields,
  IfuFieldName,
  IFU_FIELD_NAMES,
} from "../types/parse";
import { apiFetch, ApiError } from "../lib/api";

export interface UseCorrectionsResult {
  fields: ParsedFields;
  dirtyFields: Set<IfuFieldName>;
  updateField: (name: IfuFieldName, value: string | string[]) => void;
  save: () => Promise<void>;
  saving: boolean;
  undo: (name: IfuFieldName) => void;
}

// @MX:NOTE: [AUTO] originalRef stores baseline values for undo and rollback on 422
// Never mutated after initialization — only reset on successful save response
export function useCorrections(
  jobId: string,
  initialFields: ParsedFields
): UseCorrectionsResult {
  const [fields, setFields] = useState<ParsedFields>({ ...initialFields });
  const [dirtyFields, setDirtyFields] = useState<Set<IfuFieldName>>(new Set());
  const [saving, setSaving] = useState(false);

  // Snapshot of original values for undo/rollback
  const originalRef = useRef<Record<IfuFieldName, string | string[] | null>>(
    Object.fromEntries(
      IFU_FIELD_NAMES.map((f) => [f, initialFields[f].value])
    ) as Record<IfuFieldName, string | string[] | null>
  );

  const updateField = useCallback((name: IfuFieldName, value: string | string[]) => {
    setFields((prev) => ({
      ...prev,
      [name]: { ...prev[name], value },
    }));
    setDirtyFields((prev) => new Set([...prev, name]));
  }, []);

  const undo = useCallback((name: IfuFieldName) => {
    const original = originalRef.current[name];
    setFields((prev) => ({
      ...prev,
      [name]: { ...prev[name], value: original },
    }));
    setDirtyFields((prev) => {
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
  }, []);

  // @MX:WARN: [AUTO] Array values are joined with \n — backend accepts string only
  // @MX:REASON: Backend CorrectionsRequest.corrections is dict[str, str]; arrays cause 422
  const save = useCallback(async () => {
    if (dirtyFields.size === 0) return;

    setSaving(true);

    // Snapshot current dirty values for potential rollback
    const snapshot = Object.fromEntries(
      [...dirtyFields].map((f) => [f, fields[f].value])
    ) as Record<IfuFieldName, string | string[] | null>;

    // Build corrections — only valid IFU field names, join arrays
    const corrections: Partial<Record<IfuFieldName, string>> = {};
    for (const name of dirtyFields) {
      if (!(IFU_FIELD_NAMES as readonly string[]).includes(name)) continue;
      const v = fields[name].value;
      corrections[name] = Array.isArray(v) ? v.join("\n") : (v ?? "");
    }

    try {
      await apiFetch(`/parse/${jobId}/corrections`, {
        method: "PATCH",
        body: JSON.stringify({ corrections }),
      });

      // On success: update originalRef so undo now tracks new baseline
      for (const name of dirtyFields) {
        originalRef.current[name] = snapshot[name];
      }
      setDirtyFields(new Set());
    } catch (err) {
      // Rollback on any error (especially 422)
      setFields((prev) => {
        const next = { ...prev };
        for (const name of dirtyFields) {
          next[name] = { ...next[name], value: originalRef.current[name] };
        }
        return next;
      });
      setDirtyFields(new Set());
      throw err;
    } finally {
      setSaving(false);
    }
  }, [jobId, dirtyFields, fields]);

  return { fields, dirtyFields, updateField, save, saving, undo };
}
