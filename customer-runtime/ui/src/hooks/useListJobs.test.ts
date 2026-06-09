import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useListJobs } from "./useListJobs";
import type { ListJobsResponse } from "../types/jobs";

const makeResponse = (overrides: Partial<ListJobsResponse> = {}): ListJobsResponse => ({
  items: [],
  total: 0,
  skip: 0,
  limit: 50,
  ...overrides,
});

describe("useListJobs", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("starts with loading=true", () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse()), { status: 200 })
    );
    const { result } = renderHook(() => useListJobs());
    expect(result.current.loading).toBe(true);
  });

  it("resolves data after successful fetch", async () => {
    const response = makeResponse({ total: 2, items: [] });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const { result } = renderHook(() => useListJobs());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.total).toBe(2);
    expect(result.current.error).toBeNull();
  });

  it("sets error on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("network fail"));
    const { result } = renderHook(() => useListJobs());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeNull();
  });

  it("builds status query param when status != 'all'", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse()), { status: 200 })
    );
    const { result } = renderHook(() => useListJobs({ status: "done" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const url = String((fetchMock.mock.calls[0] as unknown[])[0]);
    expect(url).toContain("status=done");
  });

  it("omits status param when status is 'all'", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse()), { status: 200 })
    );
    const { result } = renderHook(() => useListJobs({ status: "all" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const url = String((fetchMock.mock.calls[0] as unknown[])[0]);
    expect(url).not.toContain("status=");
  });

  it("includes skip and limit in query", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse()), { status: 200 })
    );
    const { result } = renderHook(() => useListJobs({ skip: 50, limit: 25 }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const url = String((fetchMock.mock.calls[0] as unknown[])[0]);
    expect(url).toContain("skip=50");
    expect(url).toContain("limit=25");
  });

  it("refetch triggers another API call", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse()), { status: 200 })
    );
    const { result } = renderHook(() => useListJobs());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    act(() => { result.current.refetch(); });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("AC-005: polls every 5s when items include a running job", async () => {
    const runningItem = {
      job_id: "r1", doc_id: "d1", status: "running" as const,
      overall_confidence: null, requires_correction: false,
      created_at: "2026-01-01T00:00:00Z", error: null,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeResponse({ items: [runningItem], total: 1 })), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    // Use fake timers AFTER setting up fetch mock
    vi.useFakeTimers();

    const { result } = renderHook(() => useListJobs());

    // Flush initial fetch (promises) without advancing time
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    const callsBefore = fetchMock.mock.calls.length;
    expect(callsBefore).toBeGreaterThanOrEqual(1);

    // Advance 5 seconds to fire polling interval
    await act(async () => {
      vi.advanceTimersByTime(5001);
    });
    await act(async () => { await Promise.resolve(); });

    expect(fetchMock.mock.calls.length).toBeGreaterThan(callsBefore);
    // Verify result still exists (no crash)
    expect(result.current).toBeDefined();
  });
});
