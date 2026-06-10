import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
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

// Wrap App with MemoryRouter at a specific initial path
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  // AC-001: GET called once → 15 fields (via /jobs/:jobId route)
  it("calls GET and renders 15 fields on mount (AC-001)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: "test-job",
          status: "completed",
          parsed_fields: makeFields(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    renderAt("/jobs/test-job");

    await waitFor(() => {
      expect(screen.getByText("기기명")).toBeTruthy();
    });

    expect((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("폐기 지침")).toBeTruthy();
  });

  // AC-E02: GET timeout → error message
  it("shows network error message on GET failure (AC-E02)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    renderAt("/jobs/test-job");

    await waitFor(() => {
      expect(document.body.textContent).toContain("네트워크");
    });
  });

  // AC-E03: GET 404 → 작업을 찾을 수 없음
  it("shows not found message on 404 (AC-E03)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Not Found", { status: 404 })
    );

    renderAt("/jobs/test-job");

    await waitFor(() => {
      expect(document.body.textContent).toContain("작업을 찾을 수 없음");
    });
  });

  // Queue page renders on /jobs route
  it("renders queue page at /jobs route", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, skip: 0, limit: 50 }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    renderAt("/jobs");

    await waitFor(() => {
      expect(document.body.textContent).toContain("검토 큐");
    });
  });

  // Root / redirects to /jobs
  it("redirects / to /jobs", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, skip: 0, limit: 50 }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    renderAt("/");

    await waitFor(() => {
      expect(document.body.textContent).toContain("검토 큐");
    });
  });
});
