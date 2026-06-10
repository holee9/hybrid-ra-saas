import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RejectedBanner } from "./RejectedBanner";

describe("RejectedBanner", () => {
  it("renders rejection message", () => {
    render(<RejectedBanner />);
    expect(
      screen.getByText("이 문서는 거부되었습니다. 문서를 다시 업로드해주세요.")
    ).toBeTruthy();
  });

  it("has warning/red styling", () => {
    const { container } = render(<RejectedBanner />);
    const banner = container.firstChild as HTMLElement;
    expect(banner.className).toMatch(/red|amber/);
  });
});
