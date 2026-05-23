'use client';
import { useState } from 'react';

export default function Navbar({ onNewStory }: { onNewStory: () => void }) {
  return (
    <nav className="bg-black text-white px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-orange-500 text-xl font-bold">⬡</span>
        <h1 className="text-lg font-bold tracking-tight">ACO Agent Dashboard</h1>
        <span className="text-xs text-gray-500 font-mono">v1.0</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onNewStory}
          className="px-3 py-1.5 text-xs font-bold text-black bg-orange-500 hover:bg-orange-400 rounded transition-colors"
        >
          + New Story
        </button>
      </div>
    </nav>
  );
}
