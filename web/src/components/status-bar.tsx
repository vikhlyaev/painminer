'use client';

import { useHealth } from '@/lib/hooks';
import { Activity, AlertCircle, CheckCircle2 } from 'lucide-react';

export function StatusBar() {
  const { data: health, isLoading, isError } = useHealth();

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm">
      {isLoading && (
        <>
          <Activity className="h-4 w-4 animate-pulse text-yellow-500" />
          <span className="text-gray-500">Connecting to API...</span>
        </>
      )}
      {isError && (
        <>
          <AlertCircle className="h-4 w-4 text-red-500" />
          <span className="text-red-500">API not available</span>
        </>
      )}
      {health && (
        <>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <span className="text-green-600">
            Connected • {health.service} v{health.version}
          </span>
        </>
      )}
    </div>
  );
}
