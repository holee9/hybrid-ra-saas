// SPEC-UI-002: Pagination controls — prev/next, page display, boundary disable
interface Props {
  total: number;
  skip: number;
  limit: number;
  onPageChange: (newSkip: number) => void;
}

export function Pagination({ total, skip, limit, onPageChange }: Props): JSX.Element | null {
  // Hide pagination when all results fit on one page
  if (total <= limit) return null;

  const currentPage = Math.floor(skip / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const isFirst = skip === 0;
  const isLast = skip + limit >= total;

  return (
    <div className="flex items-center justify-center gap-4 mt-4">
      <button
        aria-label="이전"
        disabled={isFirst}
        onClick={() => onPageChange(Math.max(0, skip - limit))}
        className="px-3 py-1 text-sm border rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100"
      >
        이전
      </button>
      <span className="text-sm text-gray-600">
        {currentPage} / {totalPages} 페이지
      </span>
      <button
        aria-label="다음"
        disabled={isLast}
        onClick={() => onPageChange(skip + limit)}
        className="px-3 py-1 text-sm border rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100"
      >
        다음
      </button>
    </div>
  );
}
