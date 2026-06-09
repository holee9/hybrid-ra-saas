import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useParseJob } from "./useParseJob";
import { ExtractionStage } from "../types/parse";

const makeField = () => ({
  value: null,
  confidence: 0.5,
  stage: "rule_based" as ExtractionStage,
  needs_correction: false,
});

const makeParsedFields = () => ({
  device_name: makeField(),
  intended_use: makeField(),
  indications: makeField(),
  contraindications: makeField(),
  warnings: makeField(),
  device_classification: makeField(),
  region_targets: makeField(),
  cybersecurity_requirements: makeField(),
  precautions: makeField(),
  product_code: makeField(),
  maintenance_interval: makeField(),
  cleaning_disinfection: makeField(),
  software_version: makeField(),
  accessories: makeField(),
  disposal_instructions: makeField(),
  overall_confidence: 0.5,
  requires_correction: false,
  rejected: false,
});

const mockResponse = {
  job_id: "job-123",
  status: "completed",
  parsed_fields: makeParsedFields(),
};

describe("useParseJob", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with loading=true", () => {
    const { result } = renderHook(() => useParseJob("job-123"));
    expect(result.current.loading).toBe(true);
  });

  it("fetches data and sets data on success", async () => {
    const { result } = renderHook(() => useParseJob("job-123"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toMatchObject({ job_id: "job-123" });
    expect(result.current.error).toBeNull();
  });

  it("calls GET /parse/jobs/{jobId}", async () => {
    renderHook(() => useParseJob("job-abc"));

    await waitFor(() =>
      expect(global.fetch as ReturnType<typeof vi.fn>).toHaveBeenCalled()
    );

    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toContain("/parse/jobs/job-abc");
  });

  it("sets error on 404", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Not Found", { status: 404 })
    );

    const { result } = renderHook(() => useParseJob("missing-job"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
  });

  it("sets error on network failure", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    const { result } = renderHook(() => useParseJob("job-123"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toContain("네트워크");
  });

  it("exposes refetch function", async () => {
    const { result } = renderHook(() => useParseJob("job-123"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(typeof result.current.refetch).toBe("function");
  });

  it("refetch re-calls the API", async () => {
    const { result } = renderHook(() => useParseJob("job-123"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    result.current.refetch();
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(2);
  });
});
