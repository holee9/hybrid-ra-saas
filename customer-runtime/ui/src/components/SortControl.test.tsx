import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SortControl } from "./SortControl";

describe("SortControl", () => {
  const defaultProps = {
    field: "created_at" as const,
    order: "desc" as const,
    onChange: vi.fn(),
  };

  it("renders as group with aria-label (WCAG 1.3.1)", () => {
    const { container } = render(<SortControl {...defaultProps} />);
    const group = container.querySelector('[role="group"]');
    expect(group).toBeTruthy();
    expect(group?.getAttribute("aria-label")).toBe("정렬 기준");
  });

  it("active button has aria-pressed=true", () => {
    render(<SortControl {...defaultProps} field="created_at" />);
    const activeBtn = screen.getByRole("button", { name: /작성일/ });
    expect(activeBtn.getAttribute("aria-pressed")).toBe("true");
  });

  it("inactive button has aria-pressed=false", () => {
    render(<SortControl {...defaultProps} field="created_at" />);
    const inactiveBtn = screen.getByRole("button", { name: /신뢰도/ });
    expect(inactiveBtn.getAttribute("aria-pressed")).toBe("false");
  });

  it("active button aria-label includes direction", () => {
    render(<SortControl {...defaultProps} field="created_at" order="desc" />);
    const btn = screen.getByRole("button", { name: /내림차순/ });
    expect(btn).toBeTruthy();
  });

  it("clicking inactive field calls onChange with that field", async () => {
    const onChange = vi.fn();
    render(<SortControl {...defaultProps} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: /신뢰도/ }));
    expect(onChange).toHaveBeenCalledWith("overall_confidence", "desc");
  });

  it("clicking active field toggles order", async () => {
    const onChange = vi.fn();
    render(<SortControl {...defaultProps} field="created_at" order="desc" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: /작성일/ }));
    expect(onChange).toHaveBeenCalledWith("created_at", "asc");
  });

  it("all buttons are keyboard-focusable", () => {
    const { container } = render(<SortControl {...defaultProps} />);
    const buttons = container.querySelectorAll("button");
    buttons.forEach((btn) => {
      expect(btn.tagName).toBe("BUTTON");
    });
  });
});
