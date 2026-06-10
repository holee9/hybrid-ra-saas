import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FieldRow } from "./FieldRow";
import { ExtractionStage } from "../types/parse";

const defaultField = {
  value: "TestDevice X100",
  confidence: 0.92,
  stage: ExtractionStage.RULE,
  needs_correction: false,
};

describe("FieldRow", () => {
  it("renders field label in Korean", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("기기명")).toBeTruthy();
  });

  it("renders field value", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("TestDevice X100")).toBeTruthy();
  });

  it("shows input on click", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    const valueEl = screen.getByText("TestDevice X100");
    fireEvent.click(valueEl);
    expect(screen.getByRole("textbox")).toBeTruthy();
  });

  it("calls onUpdate when input changes", () => {
    const onUpdate = vi.fn();
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={onUpdate}
      />
    );
    fireEvent.click(screen.getByText("TestDevice X100"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "New Device" } });
    expect(onUpdate).toHaveBeenCalledWith("New Device");
  });

  it("shows yellow border when isDirty=true", () => {
    const { container } = render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={true}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(container.firstChild).toHaveClass("border-l-yellow-400");
  });

  it("does NOT show yellow border when isDirty=false", () => {
    const { container } = render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(container.firstChild).not.toHaveClass("border-l-yellow-400");
  });

  it("renders array values as newline-joined text", () => {
    render(
      <FieldRow
        fieldName="warnings"
        extraction={{ ...defaultField, value: ["Warning A", "Warning B"] }}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Warning A\nWarning B", { normalizer: (s) => s })).toBeTruthy();
  });

  it("shows placeholder for null value", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={{ ...defaultField, value: null }}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("(없음)")).toBeTruthy();
  });

  it("disables click-to-edit when disabled=true", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={true}
        onUpdate={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText("TestDevice X100"));
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("renders ConfidenceBadge and StageIndicator", () => {
    render(
      <FieldRow
        fieldName="device_name"
        extraction={defaultField}
        isDirty={false}
        disabled={false}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("0.92")).toBeTruthy(); // ConfidenceBadge
    expect(screen.getByText("규칙 기반")).toBeTruthy(); // StageIndicator
  });
});
