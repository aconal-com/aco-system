'use client';
import type { StoryStatus } from '@/lib/types';

const STATUS_COLORS: Record<StoryStatus, { bg: string; text: string; dot: string }> = {
  PM_REVIEW:     { bg: 'bg-orange-100',   text: 'text-orange-700',   dot: 'bg-orange-500' },
  PLANNER:       { bg: 'bg-blue-100',     text: 'text-blue-700',     dot: 'bg-blue-500' },
  ARCHITECT:     { bg: 'bg-purple-100',   text: 'text-purple-700',   dot: 'bg-purple-500' },
  DEV:           { bg: 'bg-green-100',    text: 'text-green-700',    dot: 'bg-green-500' },
  QA:            { bg: 'bg-red-100',      text: 'text-red-700',      dot: 'bg-red-500' },
  HUMAN_REVIEW:  { bg: 'bg-gray-200',     text: 'text-gray-700',     dot: 'bg-gray-600' },
  DONE:          { bg: 'bg-green-200',    text: 'text-green-800',    dot: 'bg-green-600' },
  BLOCKED:       { bg: 'bg-red-200',      text: 'text-red-800',      dot: 'bg-red-700' },
};

const STATUS_LABELS: Record<StoryStatus, string> = {
  PM_REVIEW: 'PM Review', PLANNER: 'Planner', ARCHITECT: 'Architect',
  DEV: 'Dev', QA: 'QA', HUMAN_REVIEW: 'Human Review', DONE: 'Done', BLOCKED: 'Blocked',
};

export default function StatusBadge({ status }: { status: StoryStatus }) {
  const c = STATUS_COLORS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {STATUS_LABELS[status]}
    </span>
  );
}
