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
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
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
            className={
              job.requires_correction
                ? "cursor-pointer hover:bg-yellow-100 bg-yellow-50 border-l-4 border-yellow-400"
                : "cursor-pointer hover:bg-gray-50"
            }
          >
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
  );
}
