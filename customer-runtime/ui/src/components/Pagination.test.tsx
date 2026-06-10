import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("returns null when total <= limit", () => {
    const { container } = render(
      <Pagination total={10} skip={0} limit={50} onPageChange={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders when total > limit", () => {
    render(
      <Pagination total={100} skip={0} limit={50} onPageChange={vi.fn()} />
    );
    expect(document.body.textContent).toContain("1");
    expect(document.body.textContent).toContain("2");
  });

  it("disables prev button on first page", () => {
    render(
      <Pagination total={100} skip={0} limit={50} onPageChange={vi.fn()} />
    );
    const prev = screen.getByRole("button", { name: /이전|prev/i });
    expect(prev).toBeDisabled();
  });

  it("disables next button on last page", () => {
    render(
      <Pagination total={100} skip={50} limit={50} onPageChange={vi.fn()} />
    );
    const next = screen.getByRole("button", { name: /다음|next/i });
    expect(next).toBeDisabled();
  });

  it("calls onPageChange with correct skip on next click", () => {
    const onPageChange = vi.fn();
    render(
      <Pagination total={100} skip={0} limit={50} onPageChange={onPageChange} />
    );
    fireEvent.click(screen.getByRole("button", { name: /다음|next/i }));
    expect(onPageChange).toHaveBeenCalledWith(50);
  });

  it("calls onPageChange with correct skip on prev click", () => {
    const onPageChange = vi.fn();
    render(
      <Pagination total={100} skip={50} limit={50} onPageChange={onPageChange} />
    );
    fireEvent.click(screen.getByRole("button", { name: /이전|prev/i }));
    expect(onPageChange).toHaveBeenCalledWith(0);
  });

  it("shows current page and total pages (AC-008 prerequisite)", () => {
    render(
      <Pagination total={150} skip={50} limit={50} onPageChange={vi.fn()} />
    );
    // Should show "2 / 3 페이지" or similar
    expect(document.body.textContent).toMatch(/2/);
    expect(document.body.textContent).toMatch(/3/);
  });
});
