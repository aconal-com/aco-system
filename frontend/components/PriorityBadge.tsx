'use client';
import type { Priority } from '@/lib/types';

const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; dot: string }> = {
  critical: { label: 'Critical', color: 'text-red-600 bg-red-50 border border-red-200', dot: 'bg-red-500' },
  high:     { label: 'High',     color: 'text-orange-600 bg-orange-50 border border-orange-200', dot: 'bg-orange-500' },
  medium:   { label: 'Medium',   color: 'text-yellow-700 bg-yellow-50 border border-yellow-200', dot: 'bg-yellow-500' },
  low:      { label: 'Low',      color: 'text-gray-500 bg-gray-50 border border-gray-200', dot: 'bg-gray-400' },
};

export default function PriorityBadge({ priority }: { priority: Priority }) {
  const p = PRIORITY_CONFIG[priority];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${p.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
      {p.label}
    </span>
  );
}
