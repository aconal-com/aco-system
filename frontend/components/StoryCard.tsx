'use client';
import type { Story } from '@/lib/types';
import StatusBadge from './StatusBadge';
import PriorityBadge from './PriorityBadge';

function timeAgo(date: string): string {
  const diff = (Date.now() - new Date(date).getTime()) / 60000;
  if (diff < 1) return 'just now';
  if (diff < 60) return `${Math.floor(diff)}m ago`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
  return `${Math.floor(diff / 1440)}d ago`;
}

interface Props {
  story: Story;
  onClick?: () => void;
}

export default function StoryCard({ story, onClick }: Props) {
  const age = Math.floor((Date.now() - new Date(story.updated_at).getTime()) / 60000);

  return (
    <div
      onClick={onClick}
      className="story-card bg-white rounded-lg border border-gray-200 p-3 cursor-pointer hover:border-orange-300"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-semibold text-gray-900 leading-tight">{story.title}</h3>
        <PriorityBadge priority={story.priority} />
      </div>

      <p className="text-xs text-gray-500 mb-2 line-clamp-2">{story.description}</p>

      <div className="flex items-center justify-between">
        <StatusBadge status={story.status} />
        <div className="flex items-center gap-2">
          {story.qa_rejections > 0 && (
            <span className="text-xs text-red-500 font-medium">
              ↩ {story.qa_rejections}
            </span>
          )}
          <span className="text-xs text-gray-400">{timeAgo(story.updated_at)}</span>
        </div>
      </div>

      {story.assignee && (
        <div className="mt-1.5 pt-1.5 border-t border-gray-100">
          <span className="text-xs text-gray-400">Assigned: </span>
          <span className="text-xs text-gray-600 font-medium">{story.assignee}</span>
        </div>
      )}
    </div>
  );
}
