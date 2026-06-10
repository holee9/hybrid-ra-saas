import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { JobQueueTable } from "./JobQueueTable";
import type { JobSummary } from "../types/jobs";

const makeJob = (overrides: Partial<JobSummary> = {}): JobSummary => ({
  job_id: "job-1",
  doc_id: "doc-1",
  status: "done",
  overall_confidence: 0.85,
  requires_correction: false,
  created_at: "2026-01-01T00:00:00Z",
  error: null,
  ...overrides,
});

describe("JobQueueTable", () => {
  it("AC-001: renders table with status, confidence, and date columns", () => {
    const jobs = [makeJob()];
    render(
      <MemoryRouter>
        <JobQueueTable items={jobs} onRowClick={vi.fn()} />
      </MemoryRouter>
    );
    // Table should be present
    expect(document.querySelector("table")).toBeTruthy();
    // Status column header
    expect(screen.getByText(/상태/)).toBeTruthy();
    // Confidence column header
    expect(screen.getByText(/신뢰도/)).toBeTruthy();
    // Date column header
    expect(screen.getByText(/작성일/)).toBeTruthy();
  });

  it("AC-003: row click calls onRowClick with job_id", () => {
    const onRowClick = vi.fn();
    const jobs = [makeJob({ job_id: "click-job" })];
    render(
      <MemoryRouter>
        <JobQueueTable items={jobs} onRowClick={onRowClick} />
      </MemoryRouter>
    );
    const rows = document.querySelectorAll("tbody tr");
    fireEvent.click(rows[0]);
    expect(onRowClick).toHaveBeenCalledWith("click-job");
  });

  it("AC-004: requires_correction row has yellow highlight", () => {
    const jobs = [makeJob({ requires_correction: true, job_id: "req-job" })];
    const { container } = render(
      <MemoryRouter>
        <JobQueueTable items={jobs} onRowClick={vi.fn()} />
      </MemoryRouter>
    );
    const row = container.querySelector("tbody tr");
    expect(row?.className).toMatch(/yellow/);
  });

  it("non-correction row does not have yellow highlight", () => {
    const jobs = [makeJob({ requires_correction: false })];
    const { container } = render(
      <MemoryRouter>
        <JobQueueTable items={jobs} onRowClick={vi.fn()} />
      </MemoryRouter>
    );
    const row = container.querySelector("tbody tr");
    expect(row?.className ?? "").not.toMatch(/yellow/);
  });

  it("shows empty state message when items is empty", () => {
    render(
      <MemoryRouter>
        <JobQueueTable items={[]} onRowClick={vi.fn()} />
      </MemoryRouter>
    );
    expect(document.body.textContent).toMatch(/없음|empty|데이터/i);
  });

  it("renders multiple rows", () => {
    const jobs = [
      makeJob({ job_id: "job-a" }),
      makeJob({ job_id: "job-b", status: "pending" }),
    ];
    render(
      <MemoryRouter>
        <JobQueueTable items={jobs} onRowClick={vi.fn()} />
      </MemoryRouter>
    );
    const rows = document.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
  });
});
