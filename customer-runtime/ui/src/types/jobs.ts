// SPEC-UI-002: JobSummary types — mirrors backend schemas/parse.py JobSummary
export interface JobSummary {
  job_id: string;
  doc_id: string;
  status: "pending" | "running" | "done" | "failed";
  overall_confidence: number | null;
  requires_correction: boolean;
  created_at: string;
  error: string | null;
}

export interface ListJobsResponse {
  items: JobSummary[];
  total: number;
  skip: number;
  limit: number;
}

export const PAGE_SIZE = 50;

export const STATUS_TABS = [
  { key: "all" as const, label: "전체" },
  { key: "pending" as const, label: "대기" },
  { key: "running" as const, label: "처리중" },
  { key: "done" as const, label: "완료" },
  { key: "failed" as const, label: "실패" },
] as const;

export type StatusTabKey = (typeof STATUS_TABS)[number]["key"];

export type SortField = "created_at" | "overall_confidence";
export type SortOrder = "desc" | "asc";
