'use client';
import type { Agent } from '@/lib/types';

function timeAgo(date: string): string {
  const diff = (Date.now() - new Date(date).getTime()) / 60000;
  if (diff < 1) return 'now';
  if (diff < 60) return `${Math.floor(diff)}m`;
  return `${Math.floor(diff / 60)}h`;
}

interface Props {
  agent: Agent;
  onTrigger?: (agentId: string) => void;
}

export default function AgentCard({ agent, onTrigger }: Props) {
  const statusClass = agent.status === 'busy' ? 'agent-busy' : agent.status === 'error' ? 'agent-error' : 'agent-idle';
  const statusDot = agent.status === 'busy' ? 'bg-orange-500 animate-pulse' : agent.status === 'error' ? 'bg-red-500' : 'bg-gray-300';
  const statusText = agent.status === 'busy' ? 'Working...' : agent.status === 'error' ? 'Error' : 'Idle';

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-3 ${statusClass} ${agent.status === 'busy' ? 'pulse-orange' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: agent.color }}>
            {agent.name.charAt(0)}
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-900">{agent.name}</div>
            <div className="text-xs text-gray-400">{agent.role}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${statusDot}`} />
          <span className="text-xs text-gray-500">{statusText}</span>
        </div>
      </div>

      {agent.current_story ? (
        <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-400 mb-0.5">Working on</div>
          <div className="text-xs font-medium text-gray-700 truncate">{agent.current_story}</div>
          {agent.started_at && (
            <div className="text-xs text-gray-400 mt-0.5">for {timeAgo(agent.started_at)}</div>
          )}
        </div>
      ) : (
        <div className="mt-2 text-xs text-gray-400 italic">No active story</div>
      )}

      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
        <span className="text-xs text-gray-400">{agent.completed_count} completed</span>
        <span className="text-xs text-gray-400">seen {timeAgo(agent.last_seen)} ago</span>
      </div>

      {agent.status === 'idle' && onTrigger && (
        <button
          onClick={() => onTrigger(agent.id)}
          className="mt-2 w-full py-1 px-2 text-xs font-medium text-orange-600 bg-orange-50 hover:bg-orange-100 rounded transition-colors"
        >
          Trigger Agent
        </button>
      )}
    </div>
  );
}
