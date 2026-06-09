export function RejectedBanner() {
  return (
    <div className="w-full flex items-center gap-3 px-4 py-3 rounded-md bg-red-50 border border-red-300 text-red-800">
      <svg
        className="w-5 h-5 shrink-0 text-red-500"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-11a1 1 0 112 0v4a1 1 0 11-2 0V7zm0 6a1 1 0 112 0 1 1 0 01-2 0z"
          clipRule="evenodd"
        />
      </svg>
      <span className="text-sm font-medium">
        이 문서는 거부되었습니다. 문서를 다시 업로드해주세요.
      </span>
    </div>
  );
}
