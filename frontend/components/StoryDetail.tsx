'use client';
import { useState } from 'react';
import type { Story } from '@/lib/types';
import StatusBadge from './StatusBadge';
import PriorityBadge from './PriorityBadge';

type Tab = 'timeline' | 'tasks' | 'context' | 'logs';

function timeAgo(date: string): string {
  const diff = (Date.now() - new Date(date).getTime()) / 60000;
  if (diff < 1) return 'just now';
  if (diff < 60) return `${Math.floor(diff)}m ago`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
  return `${Math.floor(diff / 1440)}d ago`;
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

const AGENT_COLORS: Record<string, string> = {
  PM: 'text-orange-600', PLANNER: 'text-blue-600', ARCHITECT: 'text-purple-600',
  DEVELOPER: 'text-green-600', QA: 'text-red-600', HUMAN: 'text-gray-600',
};

interface Props { story: Story; onClose: () => void; }

export default function StoryDetail({ story, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('timeline');

  return (
    <div className="flex-shrink-0 w-96 bg-white border-l border-gray-200 flex flex-col max-h-screen overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-gray-900 truncate">{story.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <StatusBadge status={story.status} />
            <PriorityBadge priority={story.priority} />
          </div>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-lg leading-none flex-shrink-0">×</button>
      </div>

      {/* Description */}
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
        <p className="text-xs text-gray-600">{story.description}</p>
        <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
          <span>Updated {timeAgo(story.updated_at)}</span>
          <span>ID: {story.id}</span>
          {story.assignee && <span>→ {story.assignee}</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(['timeline', 'tasks', 'context', 'logs'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 px-3 py-2 text-xs font-medium capitalize transition-colors ${
              tab === t ? 'text-orange-600 border-b-2 border-orange-500 bg-orange-50' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'context' ? 'JSON' : t}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'timeline' && (
          <div className="p-3 space-y-0">
            {story.timeline && story.timeline.length > 0 ? (
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
                {story.timeline.map((ev, i) => (
                  <div key={i} className="relative flex gap-3 mb-4 pl-8">
                    <div className="absolute left-3 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-orange-400 border-2 border-white ring-2 ring-orange-100" />
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`text-xs font-bold uppercase ${AGENT_COLORS[ev.agent] ?? 'text-gray-600'}`}>
                          {ev.agent}
                        </span>
                        <span className="text-xs font-semibold text-gray-700">{ev.action}</span>
                      </div>
                      <p className="text-xs text-gray-600">{ev.detail}</p>
                      <span className="text-xs text-gray-300">{formatTs(ev.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">No timeline events yet</p>
            )}
          </div>
        )}

        {tab === 'tasks' && (
          <div className="p-3 space-y-2">
            {story.tasks && story.tasks.length > 0 ? (
              story.tasks.map(task => (
                <div key={task.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded border border-gray-100">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    task.status === 'done' ? 'bg-green-500' : task.status === 'in_progress' ? 'bg-orange-400' : 'bg-gray-300'
                  }`} />
                  <span className={`text-xs flex-1 ${task.status === 'done' ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                    {task.title}
                  </span>
                  {task.assignee && <span className="text-xs text-gray-400">{task.assignee}</span>}
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">No tasks yet</p>
            )}
          </div>
        )}

        {tab === 'context' && (
          <div className="p-3">
            <pre className="text-xs text-gray-700 bg-gray-900 text-green-400 p-3 rounded overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(story.context ?? { story_id: story.id, status: story.status, priority: story.priority, tags: story.tags }, null, 2)}
            </pre>
          </div>
        )}

        {tab === 'logs' && (
          <div className="p-3">
            <pre className="text-xs text-gray-500 font-mono bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto">
{story.timeline ? story.timeline.map((ev, i) =>
  `[${formatTs(ev.timestamp)}] ${ev.agent}: ${ev.action} — ${ev.detail}`
).join('\n') : 'No logs available'}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
