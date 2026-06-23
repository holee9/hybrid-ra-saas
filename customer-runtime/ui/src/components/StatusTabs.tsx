// SPEC-UI-002: Tab navigation for filtering parse jobs by status
import { STATUS_TABS, type StatusTabKey } from "../types/jobs";

interface Props {
  active: StatusTabKey;
  onChange: (key: StatusTabKey) => void;
}

export function StatusTabs({ active, onChange }: Props): JSX.Element {
  return (
    <div role="tablist" aria-label="작업 상태 필터" className="flex gap-1 border-b border-gray-200 mb-4">
      {STATUS_TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={
              isActive
                ? "px-4 py-2 text-sm font-semibold text-blue-600 border-b-2 border-blue-600 -mb-px"
                : "px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            }
            aria-selected={isActive}
            role="tab"
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
