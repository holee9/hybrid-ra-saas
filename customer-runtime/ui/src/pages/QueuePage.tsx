// SPEC-UI-002: Review queue page — compose all queue sub-components
import { useNavigate, useSearchParams } from "react-router-dom";
import type { SortField, SortOrder, StatusTabKey } from "../types/jobs";
import { PAGE_SIZE } from "../types/jobs";
import { useListJobs } from "../hooks/useListJobs";
import { StatusTabs } from "../components/StatusTabs";
import { SortControl } from "../components/SortControl";
import { JobQueueTable } from "../components/JobQueueTable";
import { Pagination } from "../components/Pagination";

const VALID_STATUSES = new Set<StatusTabKey>(["all", "pending", "running", "done", "failed"]);
const VALID_SORT_FIELDS = new Set<SortField>(["created_at", "overall_confidence"]);
const VALID_SORT_ORDERS = new Set<SortOrder>(["asc", "desc"]);

function parseStatus(raw: string | null): StatusTabKey {
  return raw && VALID_STATUSES.has(raw as StatusTabKey) ? (raw as StatusTabKey) : "all";
}
function parseSortField(raw: string | null): SortField {
  return raw && VALID_SORT_FIELDS.has(raw as SortField) ? (raw as SortField) : "created_at";
}
function parseSortOrder(raw: string | null): SortOrder {
  return raw && VALID_SORT_ORDERS.has(raw as SortOrder) ? (raw as SortOrder) : "desc";
}
function parsePage(raw: string | null): number {
  const n = parseInt(raw ?? "1", 10);
  return isNaN(n) || n < 1 ? 1 : n;
}

export function QueuePage(): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const status = parseStatus(searchParams.get("status"));
  const sortField = parseSortField(searchParams.get("sort"));
  const sortOrder = parseSortOrder(searchParams.get("order"));
  const page = parsePage(searchParams.get("page"));
  const skip = (page - 1) * PAGE_SIZE;

  const { data, loading, error } = useListJobs({
    status,
    skip,
    limit: PAGE_SIZE,
    sortField,
    sortOrder,
  });

  function handleStatusChange(key: StatusTabKey) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("status", key);
      next.delete("page"); // Reset pagination on tab change (AC-002)
      return next;
    });
  }

  function handleSortChange(field: SortField, order: SortOrder) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("sort", field);
      next.set("order", order);
      return next;
    });
  }

  function handlePageChange(newSkip: number) {
    const newPage = Math.floor(newSkip / PAGE_SIZE) + 1;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (newPage === 1) {
        next.delete("page");
      } else {
        next.set("page", String(newPage));
      }
      return next;
    });
  }

  function handleRowClick(jobId: string) {
    navigate(`/jobs/${jobId}`);
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-gray-900 mb-4">검토 큐</h1>

      <StatusTabs active={status} onChange={handleStatusChange} />
      <SortControl field={sortField} order={sortOrder} onChange={handleSortChange} />

      {loading && (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
        </div>
      )}

      {error && !loading && (
        <div className="text-red-600 text-sm py-6 text-center">{error}</div>
      )}

      {!loading && !error && data && (
        <>
          <JobQueueTable items={data.items} onRowClick={handleRowClick} />
          <Pagination
            total={data.total}
            skip={data.skip}
            limit={data.limit}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );
}
