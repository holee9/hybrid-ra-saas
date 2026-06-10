// @MX:WARN: [AUTO] setInterval polling — clearInterval required in useEffect cleanup
// @MX:REASON: Memory leak if interval not cleared on unmount or dependency change
import { useState, useEffect, useCallback, useRef } from "react";
import type { ListJobsResponse, SortField, SortOrder, StatusTabKey } from "../types/jobs";
import { PAGE_SIZE } from "../types/jobs";
import { apiFetch } from "../lib/api";

export interface UseListJobsOptions {
  status?: StatusTabKey;
  skip?: number;
  limit?: number;
  sortField?: SortField;
  sortOrder?: SortOrder;
}

export interface UseListJobsResult {
  data: ListJobsResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function buildQueryString(options: UseListJobsOptions): string {
  const params = new URLSearchParams();
  const skip = options.skip ?? 0;
  const limit = options.limit ?? PAGE_SIZE;
  params.set("skip", String(skip));
  params.set("limit", String(limit));
  // Omit status param when "all" — backend interprets absence as all
  if (options.status && options.status !== "all") {
    params.set("status", options.status);
  }
  return params.toString();
}

function sortItems(items: ListJobsResponse["items"], field?: SortField, order?: SortOrder) {
  if (!field) return items;
  const dir = order === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    if (field === "overall_confidence") {
      const av = a.overall_confidence ?? -1;
      const bv = b.overall_confidence ?? -1;
      return (av - bv) * dir;
    }
    // created_at: ISO string comparison works lexicographically
    return a.created_at.localeCompare(b.created_at) * dir;
  });
}

export function useListJobs(options?: UseListJobsOptions): UseListJobsResult {
  const [data, setData] = useState<ListJobsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  const optStatus = options?.status;
  const optSkip = options?.skip ?? 0;
  const optLimit = options?.limit ?? PAGE_SIZE;
  const optSortField = options?.sortField;
  const optSortOrder = options?.sortOrder;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const qs = buildQueryString({ status: optStatus, skip: optSkip, limit: optLimit });

    apiFetch(`/parse/jobs?${qs}`)
      .then((res) => res.json())
      .then((json: ListJobsResponse) => {
        if (!cancelled) {
          const sorted: ListJobsResponse = {
            ...json,
            items: sortItems(json.items, optSortField, optSortOrder),
          };
          setData(sorted);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("목록을 불러오지 못했습니다. 재시도해주세요.");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [optStatus, optSkip, optLimit, optSortField, optSortOrder, tick]);

  // Polling: re-fetch every 5s when any item has status==="running"
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    const hasRunning = dataRef.current?.items.some((item) => item.status === "running");
    if (!hasRunning) return;

    const id = setInterval(() => {
      setTick((t) => t + 1);
    }, 5000);

    return () => clearInterval(id);
  }, [data]);

  return { data, loading, error, refetch };
}
