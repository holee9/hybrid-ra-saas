import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { ToastProvider, useToast } from "./toast";

function TestTrigger({ message = "테스트 메시지", type = "info" as const }) {
  const { showToast } = useToast();
  return (
    <button onClick={() => showToast(message, type)}>
      toast
    </button>
  );
}

function renderAndTrigger(type = "info" as const) {
  render(
    <ToastProvider>
      <TestTrigger type={type} />
    </ToastProvider>
  );
  act(() => {
    fireEvent.click(screen.getByRole("button", { name: "toast" }));
  });
}

describe("ToastContainer accessibility (WCAG 4.1.3)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runAllTimers();
    vi.useRealTimers();
  });

  it("info toast has role=status and aria-live=polite", () => {
    renderAndTrigger("info");
    const toast = document.querySelector('[role="status"]');
    expect(toast).toBeTruthy();
    expect(toast?.getAttribute("aria-live")).toBe("polite");
    expect(toast?.getAttribute("aria-atomic")).toBe("true");
  });

  it("success toast has role=status and aria-live=polite", () => {
    renderAndTrigger("success");
    const toast = document.querySelector('[role="status"]');
    expect(toast).toBeTruthy();
    expect(toast?.getAttribute("aria-live")).toBe("polite");
  });

  it("error toast has role=alert and aria-live=assertive", () => {
    renderAndTrigger("error");
    const toast = document.querySelector('[role="alert"]');
    expect(toast).toBeTruthy();
    expect(toast?.getAttribute("aria-live")).toBe("assertive");
    expect(toast?.getAttribute("aria-atomic")).toBe("true");
  });

  it("container region has aria-label", () => {
    renderAndTrigger();
    const region = document.querySelector('[role="region"]');
    expect(region?.getAttribute("aria-label")).toBe("알림");
  });

  it("dismiss button has aria-label", () => {
    renderAndTrigger();
    const dismiss = screen.getByRole("button", { name: "닫기" });
    expect(dismiss).toBeTruthy();
  });

  it("toast disappears after 4 seconds", () => {
    renderAndTrigger();
    expect(document.querySelector('[role="status"]')).toBeTruthy();
    act(() => { vi.advanceTimersByTime(4001); });
    expect(document.querySelector('[role="status"]')).toBeNull();
  });

  it("dismiss button removes toast immediately", () => {
    renderAndTrigger();
    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    });
    expect(document.querySelector('[role="status"]')).toBeNull();
  });
});
