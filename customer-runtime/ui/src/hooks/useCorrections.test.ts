import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCorrections } from "./useCorrections";
import { ExtractionStage, IFU_FIELD_NAMES, ParsedFields } from "../types/parse";

function makeField(value: string | string[] | null = null) {
  return {
    value,
    confidence: 0.9,
    stage: ExtractionStage.RULE,
    needs_correction: false,
  };
}

function makeFields(): ParsedFields {
  const fields: Record<string, unknown> = {
    overall_confidence: 0.9,
    requires_correction: false,
    rejected: false,
  };
  IFU_FIELD_NAMES.forEach((f) => {
    fields[f] = makeField();
  });
  return fields as unknown as ParsedFields;
}

describe("useCorrections", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => vi.restoreAllMocks());

  it("initializes with no dirty fields", () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );
    expect(result.current.dirtyFields.size).toBe(0);
  });

  it("marks field as dirty after update", () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    act(() => {
      result.current.updateField("device_name", "New Device");
    });

    expect(result.current.dirtyFields.has("device_name")).toBe(true);
  });

  it("updateField updates field value in state", () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    act(() => {
      result.current.updateField("device_name", "Updated Name");
    });

    expect(result.current.fields.device_name.value).toBe("Updated Name");
  });

  it("PATCH body contains ONLY dirty fields (AC-004)", async () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    act(() => {
      result.current.updateField("device_name", "Changed Name");
    });

    await act(async () => {
      await result.current.save();
    });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const body = JSON.parse(init.body as string);
    expect(Object.keys(body.corrections)).toEqual(["device_name"]);
    expect(body.corrections.device_name).toBe("Changed Name");
  });

  it("joins array values with \\n before sending PATCH", async () => {
    const fields = makeFields();
    fields.warnings = makeField(["Warning A", "Warning B"]);
    const { result } = renderHook(() => useCorrections("job-1", fields));

    act(() => {
      result.current.updateField("warnings", "Warning A\nWarning B\nWarning C");
    });

    await act(async () => {
      await result.current.save();
    });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const body = JSON.parse(init.body as string);
    expect(typeof body.corrections.warnings).toBe("string");
  });

  it("clears dirty fields after successful save", async () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    act(() => {
      result.current.updateField("device_name", "Changed");
    });

    await act(async () => {
      await result.current.save();
    });

    expect(result.current.dirtyFields.size).toBe(0);
  });

  it("rolls back on 422 (AC-006)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Unprocessable", { status: 422 })
    );

    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );
    const originalValue = result.current.fields.device_name.value;

    act(() => {
      result.current.updateField("device_name", "BadValue");
    });

    await act(async () => {
      try {
        await result.current.save();
      } catch {
        // expected
      }
    });

    expect(result.current.fields.device_name.value).toBe(originalValue);
  });

  it("undo restores field to original value", () => {
    const fields = makeFields();
    fields.device_name = makeField("Original Name");
    const { result } = renderHook(() => useCorrections("job-1", fields));

    act(() => {
      result.current.updateField("device_name", "Changed Name");
    });
    expect(result.current.fields.device_name.value).toBe("Changed Name");

    act(() => {
      result.current.undo("device_name");
    });
    expect(result.current.fields.device_name.value).toBe("Original Name");
    expect(result.current.dirtyFields.has("device_name")).toBe(false);
  });

  it("saving=true during PATCH, false after", async () => {
    let resolveFetch!: (v: Response) => void;
    vi.spyOn(globalThis, "fetch").mockReturnValue(
      new Promise((res) => { resolveFetch = res; })
    );

    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    act(() => {
      result.current.updateField("device_name", "x");
    });

    let savePromise: Promise<void>;
    act(() => {
      savePromise = result.current.save();
    });

    expect(result.current.saving).toBe(true);

    resolveFetch(new Response(JSON.stringify({}), { status: 200 }));
    await act(async () => { await savePromise; });

    expect(result.current.saving).toBe(false);
  });

  it("validates field names against whitelist before PATCH", async () => {
    const { result } = renderHook(() =>
      useCorrections("job-1", makeFields())
    );

    // Even if somehow an invalid key slipped in, save should only
    // send valid IFU_FIELD_NAMES keys
    act(() => {
      result.current.updateField("device_name", "Valid");
    });

    await act(async () => {
      await result.current.save();
    });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const body = JSON.parse(init.body as string);
    const sentKeys = Object.keys(body.corrections);
    sentKeys.forEach((k) => {
      expect(IFU_FIELD_NAMES as readonly string[]).toContain(k);
    });
  });
});
