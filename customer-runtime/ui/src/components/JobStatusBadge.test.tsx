import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobStatusBadge } from "./JobStatusBadge";

describe("JobStatusBadge", () => {
  it("renders 'pending' with gray style", () => {
    const { container } = render(<JobStatusBadge status="pending" />);
    expect(container.textContent).toContain("대기");
    const span = container.querySelector("span");
    expect(span?.className).toMatch(/gray/);
  });

  it("renders 'running' with blue style", () => {
    const { container } = render(<JobStatusBadge status="running" />);
    expect(container.textContent).toContain("처리중");
    const span = container.querySelector("span");
    expect(span?.className).toMatch(/blue/);
  });

  it("renders 'done' with green style", () => {
    const { container } = render(<JobStatusBadge status="done" />);
    expect(container.textContent).toContain("완료");
    const span = container.querySelector("span");
    expect(span?.className).toMatch(/green/);
  });

  it("renders 'failed' with red style", () => {
    const { container } = render(<JobStatusBadge status="failed" />);
    expect(container.textContent).toContain("실패");
    const span = container.querySelector("span");
    expect(span?.className).toMatch(/red/);
  });
});
