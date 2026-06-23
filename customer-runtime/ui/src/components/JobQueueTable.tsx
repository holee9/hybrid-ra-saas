// SPEC-UI-002: Review queue table — status/confidence/date columns, correction highlight
import type { JobSummary } from "../types/jobs";
import { JobStatusBadge } from "./JobStatusBadge";

interface Props {
  items: JobSummary[];
  onRowClick: (jobId: string) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatConfidence(value: number | null): string {
  if (value === null) return "—";
  return `${Math.round(value * 100)}%`;
}

export function JobQueueTable({ items, onRowClick }: Props): JSX.Element {
  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 text-sm">
        데이터 없음
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse min-w-[520px]">
        <caption className="sr-only">작업 목록</caption>
        <thead>
          <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
            <th className="px-4 py-3">문서 ID</th>
            <th className="px-4 py-3">상태</th>
            <th className="px-4 py-3">신뢰도</th>
            <th className="px-4 py-3">작성일</th>
          </tr>
        </thead>
        <tbody>
          {items.map((job) => (
            <tr
              key={job.job_id}
              onClick={() => onRowClick(job.job_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onRowClick(job.job_id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`문서 ${job.doc_id} 상세 보기`}
              className={
                job.requires_correction
                  ? "cursor-pointer hover:bg-yellow-100 bg-yellow-50 border-l-4 border-yellow-400 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                  : "cursor-pointer hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              }
            >
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                {job.doc_id}
              </td>
              <td className="px-4 py-3">
                <JobStatusBadge status={job.status} />
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {formatConfidence(job.overall_confidence)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {formatDate(job.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
