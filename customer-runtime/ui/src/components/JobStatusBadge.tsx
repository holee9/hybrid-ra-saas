// SPEC-UI-002: Status badge for parse job status
import type { JobSummary } from "../types/jobs";

interface Props {
  status: JobSummary["status"];
}

const STATUS_CONFIG: Record<JobSummary["status"], { label: string; className: string }> = {
  pending: { label: "대기", className: "bg-gray-100 text-gray-700" },
  running: { label: "처리중", className: "bg-blue-100 text-blue-700" },
  done: { label: "완료", className: "bg-green-100 text-green-700" },
  failed: { label: "실패", className: "bg-red-100 text-red-700" },
};

export function JobStatusBadge({ status }: Props): JSX.Element {
  const config = STATUS_CONFIG[status] ?? { label: status, className: "bg-gray-100 text-gray-700" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
