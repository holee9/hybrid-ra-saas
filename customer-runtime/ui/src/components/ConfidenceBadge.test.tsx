import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "./ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("shows green for confidence >= 0.85", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.92} needs_correction={false} />
    );
    expect(screen.getByText("0.92")).toBeTruthy();
    expect(container.firstChild).toHaveClass("bg-green-100");
  });

  it("shows green at exactly 0.85", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.85} needs_correction={false} />
    );
    expect(container.firstChild).toHaveClass("bg-green-100");
  });

  it("shows yellow for 0.75 <= confidence < 0.85", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.80} needs_correction={false} />
    );
    expect(screen.getByText("0.80")).toBeTruthy();
    expect(container.firstChild).toHaveClass("bg-yellow-100");
  });

  it("shows yellow at exactly 0.75", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.75} needs_correction={false} />
    );
    expect(container.firstChild).toHaveClass("bg-yellow-100");
  });

  it("shows red for confidence < 0.75", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.60} needs_correction={false} />
    );
    expect(screen.getByText("0.60")).toBeTruthy();
    expect(container.firstChild).toHaveClass("bg-red-100");
  });

  it("shows red when needs_correction=true even if confidence is high", () => {
    const { container } = render(
      <ConfidenceBadge confidence={0.92} needs_correction={true} />
    );
    expect(container.firstChild).toHaveClass("bg-red-100");
  });

  it("displays confidence as 2-decimal string", () => {
    render(<ConfidenceBadge confidence={0.9} needs_correction={false} />);
    expect(screen.getByText("0.90")).toBeTruthy();
  });

  it("displays 0.00 for zero confidence", () => {
    render(<ConfidenceBadge confidence={0} needs_correction={true} />);
    expect(screen.getByText("0.00")).toBeTruthy();
  });
});
