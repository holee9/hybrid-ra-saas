import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StageIndicator } from "./StageIndicator";
import { ExtractionStage } from "../types/parse";

describe("StageIndicator", () => {
  it("shows '규칙 기반' for rule_based", () => {
    render(<StageIndicator stage={ExtractionStage.RULE} />);
    expect(screen.getByText("규칙 기반")).toBeTruthy();
  });

  it("shows 'NER' for spacy_ner", () => {
    render(<StageIndicator stage={ExtractionStage.NER} />);
    expect(screen.getByText("NER")).toBeTruthy();
  });

  it("shows 'LLM' for llm_fallback", () => {
    render(<StageIndicator stage={ExtractionStage.LLM} />);
    expect(screen.getByText("LLM")).toBeTruthy();
  });

  it("shows '수동' for none", () => {
    render(<StageIndicator stage={ExtractionStage.NONE} />);
    expect(screen.getByText("수동")).toBeTruthy();
  });
});
