import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toasts: Toast[];
  showToast: (message: string, type?: ToastType) => void;
  dismissToast: (id: number) => void;
}

let nextId = 0;

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "info") => {
      const id = ++nextId;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => dismissToast(id), 4000);
    },
    [dismissToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToast(): Pick<ToastContextValue, "showToast"> {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return { showToast: ctx.showToast };
}

function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div
      role="region"
      aria-label="알림"
      className="fixed bottom-4 right-4 flex flex-col gap-2 z-50"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={`flex items-center gap-3 px-4 py-3 rounded shadow-lg text-sm font-medium min-w-[240px] ${
            t.type === "success"
              ? "bg-green-600 text-white"
              : t.type === "error"
                ? "bg-red-600 text-white"
                : "bg-gray-800 text-white"
          }`}
        >
          <span className="flex-1">{t.message}</span>
          <button
            onClick={() => onDismiss(t.id)}
            className="ml-2 opacity-70 hover:opacity-100"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
