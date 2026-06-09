import { useParseJob } from "./hooks/useParseJob";
import { CorrectionPanel } from "./components/CorrectionPanel";
import { ToastProvider } from "./lib/toast";

// Job ID from URL query param: ?job_id=xxx
function getJobId(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("job_id") ?? "";
}

function AppContent() {
  const jobId = getJobId();
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
      <AppContent />
    </ToastProvider>
  );
}
