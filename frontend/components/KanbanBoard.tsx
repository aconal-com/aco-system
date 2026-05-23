'use client';
import { useState } from 'react';
import type { Story, StoryStatus } from '@/lib/types';
import StoryCard from './StoryCard';
import StoryDetail from './StoryDetail';

const COLUMNS: { id: StoryStatus; label: string; color: string }[] = [
  { id: 'PM_REVIEW',    label: 'PM Review',    color: 'border-orange-500' },
  { id: 'PLANNER',      label: 'Planner',      color: 'border-blue-500' },
  { id: 'ARCHITECT',    label: 'Architect',    color: 'border-purple-500' },
  { id: 'DEV',          label: 'Dev',          color: 'border-green-500' },
  { id: 'QA',           label: 'QA',           color: 'border-red-500' },
  { id: 'HUMAN_REVIEW', label: 'Human Review', color: 'border-gray-600' },
  { id: 'DONE',         label: 'Done',         color: 'border-green-600' },
  { id: 'BLOCKED',      label: 'Blocked',      color: 'border-red-700' },
];

interface Props { stories: Story[]; }

export default function KanbanBoard({ stories }: Props) {
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map(col => (
        <div key={col.id} className="flex-shrink-0 w-72">
          <div className={`border-t-2 ${col.color} bg-white rounded-b-lg`}>
            <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">{col.label}</span>
              <span className="text-xs text-gray-400 font-medium">
                {stories.filter(s => s.status === col.id).length}
              </span>
            </div>
            <div className="p-2 space-y-2 kanban-col">
              {stories
                .filter(s => s.status === col.id)
                .sort((a, b) => {
                  const p = { critical: 0, high: 1, medium: 2, low: 3 };
                  return p[a.priority] - p[b.priority];
                })
                .map(story => (
                  <StoryCard
                    key={story.id}
                    story={story}
                    onClick={() => setSelectedStory(story)}
                  />
                ))}
            </div>
          </div>
        </div>
      ))}

      {selectedStory && (
        <StoryDetail
          story={selectedStory}
          onClose={() => setSelectedStory(null)}
        />
      )}
    </div>
  );
}
