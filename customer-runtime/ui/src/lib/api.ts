// @MX:ANCHOR: [AUTO] apiFetch — central HTTP client for all API calls
// @MX:REASON: Called by useParseJob, useCorrections, and any future API hooks (fan_in >= 3)

// JWT stored in memory only — NOT localStorage/sessionStorage (§8 Security)
// @MX:NOTE: [AUTO] Token in module-level variable: cleared on page reload by design
let _token: string | null = null;

export const setToken = (t: string): void => {
  _token = t;
};

export const clearToken = (): void => {
  _token = null;
};

export const getToken = (): string | null => _token;

// Resolved at bundle time from env vars
const TENANT_ID: string = import.meta.env["VITE_TENANT_ID"] ?? "";
const BASE_URL: string = import.meta.env["VITE_API_BASE_URL"] ?? "/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// @MX:WARN: [AUTO] Throws ApiError on non-2xx — callers must handle 401/404/422 separately
// @MX:REASON: Unhandled errors propagate silently if callers don't discriminate by status
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };

  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  // X-Tenant-ID from env var only — never from user input
  if (TENANT_ID) {
    headers["X-Tenant-ID"] = TENANT_ID;
  }

  const url = path.startsWith("http") ? path : `${BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers });
  } catch {
    throw new ApiError(0, "네트워크 오류. 재시도해주세요.");
  }

  if (!response.ok) {
    throw new ApiError(response.status, `HTTP ${response.status}`);
  }

  return response;
}
