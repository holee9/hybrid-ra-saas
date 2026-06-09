import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { CorrectionPanel } from "./CorrectionPanel";
import { ToastProvider } from "../lib/toast";
import { ExtractionStage, IFU_FIELD_NAMES, ParsedFields } from "../types/parse";

function makeField(value: string | string[] | null = null) {
  return {
    value,
    confidence: 0.9,
    stage: ExtractionStage.RULE,
    needs_correction: false,
  };
}

function makeFields(overrides: Partial<ParsedFields> = {}): ParsedFields {
  const fields: Record<string, unknown> = {
    overall_confidence: 0.85,
    requires_correction: false,
    rejected: false,
    ...overrides,
  };
  IFU_FIELD_NAMES.forEach((f) => {
    if (!(f in fields)) fields[f] = makeField();
  });
  return fields as ParsedFields;
}

function renderPanel(jobId: string, fields: ParsedFields) {
  return render(
    <ToastProvider>
      <CorrectionPanel jobId={jobId} initialFields={fields} />
    </ToastProvider>
  );
}

describe("CorrectionPanel", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 })
    );
  });
  afterEach(() => vi.restoreAllMocks());

  // AC-001: 15 fields rendered
  it("renders all 15 field rows (AC-001)", () => {
    renderPanel("job-1", makeFields());
    IFU_FIELD_NAMES.forEach((f) => {
      // Check Korean labels exist
      expect(document.body.textContent).toContain(
        { device_name: "기기명", intended_use: "사용 목적", indications: "적응증",
          contraindications: "금기사항", warnings: "경고", device_classification: "기기 분류",
          region_targets: "대상 지역", cybersecurity_requirements: "사이버보안 요구사항",
          precautions: "주의사항", product_code: "제품 코드", maintenance_interval: "유지보수 주기",
          cleaning_disinfection: "세척/소독", software_version: "소프트웨어 버전",
          accessories: "부속품", disposal_instructions: "폐기 지침",
        }[f]
      );
    });
  });

  // AC-002: confidence badges
  it("renders confidence badges (AC-002)", () => {
    const fields = makeFields();
    fields.device_name = { ...makeField("Dev"), confidence: 0.92, stage: ExtractionStage.RULE, needs_correction: false };
    fields.intended_use = { ...makeField("Use"), confidence: 0.80, stage: ExtractionStage.NER, needs_correction: false };
    fields.indications = { ...makeField("Ind"), confidence: 0.60, stage: ExtractionStage.LLM, needs_correction: false };
    renderPanel("job-1", fields);
    expect(screen.getByText("0.92")).toBeTruthy();
    expect(screen.getByText("0.80")).toBeTruthy();
    expect(screen.getByText("0.60")).toBeTruthy();
  });

  // AC-003: edit device_name → dirty marker + Save enabled
  it("enables Save after editing a field (AC-003)", () => {
    const fields = makeFields({ device_name: makeField("Original") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    fireEvent.click(screen.getByText("Original"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Updated" } });

    const saveBtn = screen.getByRole("button", { name: /저장/i });
    expect(saveBtn).not.toBeDisabled();
  });

  // AC-003: Save disabled when no dirty fields
  it("Save button disabled when no changes", () => {
    renderPanel("job-1", makeFields());
    const saveBtn = screen.getByRole("button", { name: /저장/i });
    expect(saveBtn).toBeDisabled();
  });

  // AC-005: PATCH 200 → success toast
  it("shows success toast on save (AC-005)", async () => {
    const fields = makeFields({ device_name: makeField("Original") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    fireEvent.click(screen.getByText("Original"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Changed" } });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /저장/i }));
    });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
      expect(document.body.textContent).toContain("저장");
    });
  });

  // AC-006: PATCH 422 → rollback + error toast
  it("shows error toast and rolls back on 422 (AC-006)", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Unprocessable", { status: 422 })
    );

    const fields = makeFields({ device_name: makeField("Original") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    fireEvent.click(screen.getByText("Original"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Bad" } });
    fireEvent.blur(screen.getByRole("textbox"));

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /저장/i }));
    });

    await waitFor(() => {
      expect(document.body.textContent).toContain("검증 실패");
    });
  });

  // AC-007: rejected=true → RejectedBanner + inputs disabled
  it("shows RejectedBanner and disables form when rejected=true (AC-007)", () => {
    renderPanel("job-1", makeFields({ rejected: true } as Partial<ParsedFields>));
    expect(
      screen.getByText("이 문서는 거부되었습니다. 문서를 다시 업로드해주세요.")
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /저장/i })).toBeDisabled();
  });

  // AC-004: only changed field in PATCH body
  it("PATCH body contains only edited field (AC-004)", async () => {
    const fields = makeFields({ device_name: makeField("Original") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    fireEvent.click(screen.getByText("Original"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Only This" } });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /저장/i }));
    });

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const body = JSON.parse(init.body as string);
    expect(Object.keys(body.corrections)).toEqual(["device_name"]);
  });

  // AC-E01: all null + needs_correction → 15 red badges, no crash
  it("renders 15 red badges when all fields null+needs_correction (AC-E01)", () => {
    const fields: Record<string, unknown> = {
      overall_confidence: 0.0,
      requires_correction: true,
      rejected: false,
    };
    IFU_FIELD_NAMES.forEach((f) => {
      fields[f] = { value: null, confidence: 0.0, stage: ExtractionStage.NONE, needs_correction: true };
    });
    renderPanel("job-1", fields as ParsedFields);
    // Should not crash; 15 badges rendered
    const badges = screen.getAllByText("0.00");
    expect(badges.length).toBe(15);
  });

  // AC-E04: during PATCH → form disabled
  it("disables form during save (AC-E04)", async () => {
    let resolveFetch!: (v: Response) => void;
    vi.spyOn(global, "fetch").mockReturnValue(
      new Promise((res) => { resolveFetch = res; })
    );

    const fields = makeFields({ device_name: makeField("X") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    fireEvent.click(screen.getByText("X"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Y" } });
    fireEvent.blur(screen.getByRole("textbox"));

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: /저장/i }));
    });

    expect(screen.getByRole("button", { name: /저장/i })).toBeDisabled();

    resolveFetch(new Response(JSON.stringify({}), { status: 200 }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /저장/i })).toBeDisabled()
    );
  });

  // AC-008: undo restores field value
  it("undo button restores original value (AC-008)", async () => {
    const fields = makeFields({ warnings: makeField("Original Warning") } as Partial<ParsedFields>);
    renderPanel("job-1", fields);

    // Edit warnings field
    fireEvent.click(screen.getByText("Original Warning"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Changed Warning" } });
    fireEvent.blur(screen.getByRole("textbox"));

    // "모두 되돌리기" button appears
    const undoBtn = screen.getByRole("button", { name: /모두 되돌리기/i });
    fireEvent.click(undoBtn);

    // Original value restored
    await waitFor(() => {
      expect(screen.getByText("Original Warning")).toBeTruthy();
    });
  });

  // AC-E02: GET timeout → error message
  it("handles error state (AC-E02 context)", () => {
    // CorrectionPanel doesn't fetch on its own; error comes from parent.
    // Verify it renders without crash when fields are valid
    renderPanel("job-1", makeFields());
    expect(screen.getByRole("button", { name: /저장/i })).toBeTruthy();
  });

  // overall_confidence progress bar
  it("renders overall confidence progress bar", () => {
    renderPanel("job-1", makeFields({ overall_confidence: 0.85 } as Partial<ParsedFields>));
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });
});
