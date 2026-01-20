'use client';

import { useJob } from '@/lib/hooks';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import type { JobStatus } from '@/lib/types';

interface JobProgressProps {
  jobId: string;
  onComplete: () => void;
}

const statusConfig: Record<JobStatus, { icon: React.ReactNode; color: string; bg: string }> = {
  pending: {
    icon: <Clock className="h-5 w-5" />,
    color: 'text-yellow-600',
    bg: 'bg-yellow-100',
  },
  running: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: 'text-indigo-600',
    bg: 'bg-indigo-100',
  },
  completed: {
    icon: <CheckCircle2 className="h-5 w-5" />,
    color: 'text-green-600',
    bg: 'bg-green-100',
  },
  failed: {
    icon: <XCircle className="h-5 w-5" />,
    color: 'text-red-600',
    bg: 'bg-red-100',
  },
};

export function JobProgress({ jobId, onComplete }: JobProgressProps) {
  const { data: job, isLoading, error } = useJob(jobId);

  if (isLoading && !job) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="p-4 bg-red-50 rounded-lg text-red-700">
        Failed to load job status
      </div>
    );
  }

  const config = statusConfig[job.status];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
          {config.icon}
        </div>
        <div>
          <h3 className="font-medium text-gray-900">
            {job.status === 'pending' && 'Waiting to start...'}
            {job.status === 'running' && 'Analysis in progress'}
            {job.status === 'completed' && 'Analysis completed!'}
            {job.status === 'failed' && 'Analysis failed'}
          </h3>
          <p className="text-sm text-gray-500">{job.message}</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Progress</span>
          <span>{job.progress}%</span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              job.status === 'failed' ? 'bg-red-500' : 
              job.status === 'completed' ? 'bg-green-500' : 'bg-indigo-500'
            }`}
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>

      {/* Error message */}
      {job.error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-4">
          {job.error}
        </div>
      )}

      {/* View results button */}
      {job.status === 'completed' && (
        <button
          onClick={onComplete}
          className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          View Results
        </button>
      )}

      {/* Job info */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 space-y-1">
          <p>Job ID: {job.job_id}</p>
          <p>Created: {new Date(job.created_at).toLocaleString()}</p>
          {job.completed_at && (
            <p>Completed: {new Date(job.completed_at).toLocaleString()}</p>
          )}
        </div>
      </div>
    </div>
  );
}
