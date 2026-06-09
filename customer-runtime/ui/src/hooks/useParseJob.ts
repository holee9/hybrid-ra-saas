import { useState, useEffect, useCallback } from "react";
import { ParseJobResponse } from "../types/parse";
import { apiFetch, ApiError } from "../lib/api";

export interface UseParseJobResult {
  data: ParseJobResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useParseJob(jobId: string): UseParseJobResult {
  const [data, setData] = useState<ParseJobResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiFetch(`/parse/jobs/${jobId}`)
      .then((res) => res.json())
      .then((json: ParseJobResponse) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          if (err instanceof ApiError) {
            if (err.status === 404) {
              setError("작업을 찾을 수 없음");
            } else if (err.status === 401) {
              setError("인증 실패");
            } else if (err.status === 0) {
              setError(err.message);
            } else {
              setError(`오류: HTTP ${err.status}`);
            }
          } else {
            setError("네트워크 오류. 재시도해주세요.");
          }
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId, tick]);

  return { data, loading, error, refetch };
}
