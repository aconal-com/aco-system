'use client';
import type { Alert } from '@/lib/types';

export default function AlertPanel({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-sm text-gray-400">No alerts — all clear</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map(alert => (
        <div
          key={alert.id}
          className={`rounded-lg border p-3 flex items-start gap-2 ${
            alert.type === 'error' ? 'bg-red-50 border-red-200' :
            alert.type === 'warning' ? 'bg-orange-50 border-orange-200' :
            'bg-blue-50 border-blue-200'
          }`}
        >
          <span className="text-sm mt-0.5">
            {alert.type === 'error' ? '🔴' : alert.type === 'warning' ? '🟠' : '🔵'}
          </span>
          <p className={`text-xs flex-1 ${alert.type === 'error' ? 'text-red-700' : alert.type === 'warning' ? 'text-orange-700' : 'text-blue-700'}`}>
            {alert.message}
          </p>
        </div>
      ))}
    </div>
  );
}
