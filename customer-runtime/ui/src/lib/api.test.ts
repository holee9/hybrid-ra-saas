import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, setToken, clearToken, getToken, ApiError } from "./api";

describe("Token management", () => {
  afterEach(() => clearToken());

  it("stores token in memory", () => {
    setToken("test-jwt");
    expect(getToken()).toBe("test-jwt");
  });

  it("clears token", () => {
    setToken("test-jwt");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    clearToken();
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearToken();
  });

  it("sends Authorization header when token is set", async () => {
    setToken("my-token");
    await apiFetch("/parse/jobs/123");

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect((init.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer my-token"
    );
  });

  it("does NOT send Authorization header when no token", async () => {
    await apiFetch("/parse/jobs/123");

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect((init.headers as Record<string, string>)["Authorization"]).toBeUndefined();
  });

  it("throws ApiError on 401", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Unauthorized", { status: 401 })
    );

    await expect(apiFetch("/parse/jobs/123")).rejects.toThrow(ApiError);
    await expect(apiFetch("/parse/jobs/123")).rejects.toMatchObject({ status: 401 });
  });

  it("throws ApiError on 404", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Not Found", { status: 404 })
    );

    await expect(apiFetch("/parse/jobs/123")).rejects.toMatchObject({ status: 404 });
  });

  it("throws ApiError on 422", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Unprocessable", { status: 422 })
    );

    await expect(apiFetch("/parse/jobs/123")).rejects.toMatchObject({ status: 422 });
  });

  it("throws network error with Korean message on fetch failure", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(apiFetch("/parse/jobs/123")).rejects.toThrow(
      "네트워크 오류. 재시도해주세요."
    );
  });

  it("does NOT use localStorage or sessionStorage", () => {
    const lsSpy = vi.spyOn(Storage.prototype, "setItem");
    const ssSpy = vi.spyOn(Storage.prototype, "getItem");

    setToken("secret-jwt");

    expect(lsSpy).not.toHaveBeenCalled();
    expect(ssSpy).not.toHaveBeenCalled();
  });

  it("sends Content-Type application/json", async () => {
    await apiFetch("/test");

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json"
    );
  });
});
