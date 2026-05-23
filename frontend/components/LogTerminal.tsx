'use client';
import { useState, useEffect, useRef } from 'react';

const LOG_LINES = [
  '2026-03-30 08:00:01 [PM] Story created: User Authentication Flow',
  '2026-03-30 08:00:03 [PM] → assigned priority: critical',
  '2026-03-30 08:01:12 [PLANNER] Picking up story-1',
  '2026-03-30 08:01:15 [PLANNER] Breaking into tasks: 5 subtasks, 8 story points',
  '2026-03-30 08:02:44 [ARCHITECT] Design review started for story-1',
  '2026-03-30 08:03:01 [ARCHITECT] ✓ OAuth2 + JWT design approved',
  '2026-03-30 08:03:30 [DEVELOPER] Starting implementation of auth flow',
  '2026-03-30 08:05:22 [DEVELOPER] → Google OAuth provider configured',
  '2026-03-30 08:07:44 [DEVELOPER] → GitHub OAuth provider configured',
  '2026-03-30 08:10:01 [DEVELOPER] → JWT token generation complete',
  '2026-03-30 08:12:30 [DEVELOPER] Self-testing: 12/12 unit tests passing',
  '2026-03-30 08:13:00 [DEVELOPER] → Moving story-1 to QA',
  '2026-03-30 08:14:12 [QA] Running test suite for story-1',
  '2026-03-30 08:14:45 [QA] → 47 tests: 44 passing, 3 failing',
  '2026-03-30 08:14:46 [QA] ↩ Rejection #1: Edge case — refresh token not rotating',
  '2026-03-30 08:20:00 [DEVELOPER] Fix applied: token rotation logic corrected',
  '2026-03-30 08:21:00 [DEVELOPER] → Re-submitting to QA',
  '2026-03-30 08:22:30 [QA] Re-running suite: 47 tests passing',
  '2026-03-30 08:23:00 [QA] ✓ All tests passing — approving story-1',
  '2026-03-30 08:23:30 [PM] Story story-1 moved to DONE',
];

export default function LogTerminal() {
  const [lines, setLines] = useState<string[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let idx = 0;
    const interval = setInterval(() => {
      if (!paused && idx < LOG_LINES.length) {
        setLines(prev => {
          const next = [...prev, LOG_LINES[idx]];
          return next.slice(-100);
        });
        idx++;
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [paused]);

  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines, paused]);

  const filtered = filter ? lines.filter(l => l.toLowerCase().includes(filter.toLowerCase())) : lines;

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <span className="text-xs font-mono text-gray-400">● agents.log — live</span>
        <div className="flex items-center gap-2">
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="filter..."
            className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded border border-gray-700 w-28 focus:outline-none focus:border-orange-500"
          />
          <button
            onClick={() => setPaused(p => !p)}
            className="text-xs px-2 py-1 rounded text-gray-400 hover:text-white transition-colors"
          >
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
        </div>
      </div>
      <div ref={scrollRef} className="h-48 overflow-y-auto p-2 space-y-0.5">
        {filtered.map((line, i) => (
          <p key={i} className={`log-line ${line.includes('[QA] ↩') ? 'text-red-400' : line.includes('✓') ? 'text-green-400' : 'text-gray-300'}`}>
            {line}
          </p>
        ))}
        {paused && <p className="text-xs text-gray-500 italic mt-2">— paused —</p>}
      </div>
    </div>
  );
}
