// SPEC-UI-002: Review queue page — compose all queue sub-components
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { SortField, SortOrder, StatusTabKey } from "../types/jobs";
import { PAGE_SIZE } from "../types/jobs";
import { useListJobs } from "../hooks/useListJobs";
import { StatusTabs } from "../components/StatusTabs";
import { SortControl } from "../components/SortControl";
import { JobQueueTable } from "../components/JobQueueTable";
import { Pagination } from "../components/Pagination";

export function QueuePage(): JSX.Element {
  const navigate = useNavigate();
  const [status, setStatus] = useState<StatusTabKey>("all");
  const [skip, setSkip] = useState(0);
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const { data, loading, error } = useListJobs({
    status,
    skip,
    limit: PAGE_SIZE,
    sortField,
    sortOrder,
  });

  function handleStatusChange(key: StatusTabKey) {
    setStatus(key);
    setSkip(0); // Reset pagination on tab change (AC-002)
  }

  function handleSortChange(field: SortField, order: SortOrder) {
    setSortField(field);
    setSortOrder(order);
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
            onPageChange={setSkip}
          />
        </>
      )}
    </div>
  );
}
