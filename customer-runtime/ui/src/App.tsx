import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { useParseJob } from "./hooks/useParseJob";
import { CorrectionPanel } from "./components/CorrectionPanel";
import { ToastProvider } from "./lib/toast";
import { QueuePage } from "./pages/QueuePage";

// Job detail route — extracts jobId from URL params instead of query string
function JobDetailRoute() {
  const { jobId = "" } = useParams<{ jobId: string }>();
  const { data, loading, error } = useParseJob(jobId);

  if (!jobId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        job_id 파라미터가 필요합니다. (?job_id=...)
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="text-red-600 font-medium">{error}</span>
        <span className="text-sm text-gray-500">네트워크 오류. 재시도해주세요.</span>
      </div>
    );
  }

  if (!data?.parsed_fields) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        작업을 찾을 수 없음
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-gray-900 mb-6">
        IFU 파싱 결과 교정
      </h1>
      <p className="text-sm text-gray-500 mb-4">작업 ID: {data.job_id}</p>
      <CorrectionPanel jobId={jobId} initialFields={data.parsed_fields} />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      {/* WCAG 2.4.1 — skip navigation link for keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:rounded focus:bg-white focus:text-blue-600 focus:underline focus:shadow-md"
      >
        본문 바로가기
      </a>
      <main id="main-content" tabIndex={-1} className="outline-none">
        <Routes>
          <Route path="/" element={<Navigate to="/jobs" replace />} />
          <Route path="/jobs" element={<QueuePage />} />
          <Route path="/jobs/:jobId" element={<JobDetailRoute />} />
        </Routes>
      </main>
    </ToastProvider>
  );
}
