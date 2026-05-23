'use client';
import { useState } from 'react';
import { Agent } from '@/lib/types';

export default function QueueControls({ agents, onRefresh }: { agents: Agent[]; onRefresh: () => void }) {
  const [loading, setLoading] = useState<string | null>(null);

  async function triggerAgent(agentId: string) {
    setLoading(agentId);
    try {
      await fetch('/api/queue', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agent: agentId }) });
    } finally {
      setLoading(null);
      onRefresh();
    }
  }

  async function runAll() {
    setLoading('all');
    for (const a of agents) {
      await fetch('/api/queue', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agent: a.id }) });
    }
    setLoading(null);
    onRefresh();
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        onClick={runAll}
        disabled={!!loading}
        className="px-3 py-1.5 text-xs font-bold text-white bg-orange-500 hover:bg-orange-600 disabled:opacity-50 rounded transition-colors"
      >
        {loading === 'all' ? 'Running...' : '▶ Run All Agents'}
      </button>
      {agents.map(a => (
        <button
          key={a.id}
          onClick={() => triggerAgent(a.id)}
          disabled={!!loading}
          className="px-2 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded transition-colors"
        >
          {loading === a.id ? '...' : `▶ ${a.name.split(' ')[0]}`}
        </button>
      ))}
      <button onClick={onRefresh} className="px-2 py-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors">
        ↻ Refresh
      </button>
    </div>
  );
}
