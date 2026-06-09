// @MX:NOTE: [AUTO] Confidence thresholds: >=0.85 green, >=0.75 yellow, <0.75 red
// needs_correction=true forces red regardless of confidence value

interface ConfidenceBadgeProps {
  confidence: number;
  needs_correction: boolean;
}

function getColor(confidence: number, needs_correction: boolean): string {
  if (needs_correction || confidence < 0.75) {
    return "bg-red-100 text-red-800 border-red-200";
  }
  if (confidence < 0.85) {
    return "bg-yellow-100 text-yellow-800 border-yellow-200";
  }
  return "bg-green-100 text-green-800 border-green-200";
}

export function ConfidenceBadge({ confidence, needs_correction }: ConfidenceBadgeProps) {
  const colorClass = getColor(confidence, needs_correction);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}
    >
      {confidence.toFixed(2)}
    </span>
  );
}
