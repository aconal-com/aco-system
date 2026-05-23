'use client';
import { useState, useEffect, useCallback } from 'react';
import type { Story, Agent, Alert, FeedEvent } from '@/lib/types';
import Navbar from '@/components/Navbar';
import AgentCard from '@/components/AgentCard';
import KanbanBoard from '@/components/KanbanBoard';
import AlertPanel from '@/components/AlertPanel';
import QueueControls from '@/components/QueueControls';
import LogTerminal from '@/components/LogTerminal';
import CreateStoryForm from '@/components/CreateStoryForm';

export default function Home() {
  const [stories, setStories] = useState<Story[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [showNewStory, setShowNewStory] = useState(false);
  const [view, setView] = useState<'board' | 'agents' | 'logs'>('board');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const refresh = useCallback(async () => {
    try {
      const [s, a, al, f] = await Promise.all([
        fetch('/api/stories').then(r => r.json()),
        fetch('/api/agents').then(r => r.json()),
        fetch('/api/alerts').then(r => r.json()),
        fetch('/api/feed').then(r => r.json()),
      ]);
      setStories(s);
      setAgents(a);
      setAlerts(al);
      setFeed(f);
      setLastRefresh(new Date());
    } catch (e) {
      console.error('Refresh failed', e);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  function timeLabel() {
    const diff = Math.floor((Date.now() - lastRefresh.getTime()) / 1000);
    return diff < 5 ? 'just now' : `${diff}s ago`;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar onNewStory={() => setShowNewStory(true)} />

      <div className="flex items-center justify-between px-6 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
          {([['board', 'Pipeline'], ['agents', 'Agents'], ['logs', 'Logs']] as const).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                view === v ? 'bg-white text-orange-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {alerts.length > 0 && (
            <span className="flex items-center gap-1 text-xs text-orange-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </span>
          )}
          <span className="text-xs text-gray-400">Updated {timeLabel()}</span>
          <QueueControls agents={agents} onRefresh={refresh} />
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {view === 'board' && (
          <div className="h-full flex">
            {/* Main Kanban */}
            <div className="flex-1 overflow-x-auto p-4">
              <KanbanBoard stories={stories} />
            </div>

            {/* Right sidebar */}
            <div className="w-72 border-l border-gray-200 bg-gray-50 overflow-y-auto p-4 space-y-4 flex-shrink-0">
              <div>
                <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Live Feed</h2>
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {feed.slice(0, 10).map(event => (
                    <div key={event.id} className="bg-white rounded border border-gray-100 p-2">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-xs font-bold text-orange-600">{event.agent_name.split(' ')[0]}</span>
                        <span className="text-xs text-gray-500">{event.event}</span>
                      </div>
                      {event.story_title && (
                        <p className="text-xs text-gray-600 truncate">→ {event.story_title}</p>
                      )}
                      <p className="text-xs text-gray-400">{event.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Alerts</h2>
                <AlertPanel alerts={alerts} />
              </div>
            </div>
          </div>
        )}

        {view === 'agents' && (
          <div className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
              {agents.map(agent => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          </div>
        )}

        {view === 'logs' && (
          <div className="p-4 max-w-5xl mx-auto">
            <LogTerminal />
          </div>
        )}
      </div>

      {showNewStory && (
        <CreateStoryForm
          onClose={() => setShowNewStory(false)}
          onCreated={refresh}
        />
      )}
    </div>
  );
}
