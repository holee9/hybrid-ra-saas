import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { ExtractionStage, IFU_FIELD_NAMES } from "./types/parse";

function makeField() {
  return { value: null, confidence: 0.8, stage: ExtractionStage.RULE, needs_correction: false };
}

function makeFields() {
  const f: Record<string, unknown> = {
    overall_confidence: 0.8,
    requires_correction: false,
    rejected: false,
  };
  IFU_FIELD_NAMES.forEach((n) => { f[n] = makeField(); });
  return f;
}

describe("App", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    Object.defineProperty(window, "location", {
      value: { search: "?job_id=test-job" },
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
    vi.restoreAllMocks();
  });

  // AC-001: GET called once → 15 fields
  it("calls GET and renders 15 fields on mount (AC-001)", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: "test-job",
          status: "completed",
          parsed_fields: makeFields(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("기기명")).toBeTruthy();
    });

    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
    expect(screen.getByText("폐기 지침")).toBeTruthy();
  });

  // AC-E02: GET timeout → error message
  it("shows network error message on GET failure (AC-E02)", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    render(<App />);

    await waitFor(() => {
      expect(document.body.textContent).toContain("네트워크");
    });
  });

  // AC-E03: GET 404 → 작업을 찾을 수 없음
  it("shows not found message on 404 (AC-E03)", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Not Found", { status: 404 })
    );

    render(<App />);

    await waitFor(() => {
      expect(document.body.textContent).toContain("작업을 찾을 수 없음");
    });
  });

  // no job_id
  it("shows guidance when no job_id in URL", () => {
    Object.defineProperty(window, "location", {
      value: { search: "" },
      writable: true,
    });
    render(<App />);
    expect(document.body.textContent).toContain("job_id");
  });
});
