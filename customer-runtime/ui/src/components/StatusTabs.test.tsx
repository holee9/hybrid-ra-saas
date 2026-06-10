import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusTabs } from "./StatusTabs";
import { STATUS_TABS } from "../types/jobs";

describe("StatusTabs", () => {
  it("renders all 5 tabs", () => {
    const onChange = vi.fn();
    render(<StatusTabs active="all" onChange={onChange} />);
    STATUS_TABS.forEach((tab) => {
      expect(screen.getByText(tab.label)).toBeTruthy();
    });
  });

  it("marks the active tab with active style", () => {
    render(<StatusTabs active="done" onChange={vi.fn()} />);
    const doneBtn = screen.getByText("완료");
    // Active tab should have distinguishing class
    expect(doneBtn.className).toMatch(/border-blue|font-semibold|text-blue/);
  });

  it("calls onChange when a tab is clicked", () => {
    const onChange = vi.fn();
    render(<StatusTabs active="all" onChange={onChange} />);
    fireEvent.click(screen.getByText("완료"));
    expect(onChange).toHaveBeenCalledWith("done");
  });

  it("calls onChange with 'all' for the 전체 tab", () => {
    const onChange = vi.fn();
    render(<StatusTabs active="done" onChange={onChange} />);
    fireEvent.click(screen.getByText("전체"));
    expect(onChange).toHaveBeenCalledWith("all");
  });
});
