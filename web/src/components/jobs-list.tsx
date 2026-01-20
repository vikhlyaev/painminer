'use client';

import { useJobs, useDeleteJob } from '@/lib/hooks';
import { Clock, Loader2, CheckCircle2, XCircle, Trash2 } from 'lucide-react';
import type { JobStatus } from '@/lib/types';

interface JobsListProps {
  onSelectJob: (jobId: string) => void;
  selectedJobId: string | null;
}

const statusIcons: Record<JobStatus, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-yellow-500" />,
  running: <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />,
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-red-500" />,
};

export function JobsList({ onSelectJob, selectedJobId }: JobsListProps) {
  const { data: jobs, isLoading } = useJobs();
  const deleteJob = useDeleteJob();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="text-center p-4 text-gray-500 text-sm">
        No jobs yet
      </div>
    );
  }

  // Sort by created_at descending
  const sortedJobs = [...jobs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-2">
      {sortedJobs.map((job) => (
        <div
          key={job.job_id}
          className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
            selectedJobId === job.job_id
              ? 'bg-indigo-50 border border-indigo-200'
              : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
          }`}
          onClick={() => onSelectJob(job.job_id)}
        >
          <div className="flex items-center gap-3">
            {statusIcons[job.status]}
            <div>
              <p className="text-sm font-medium text-gray-900 truncate max-w-[150px]">
                {job.message || 'Analysis job'}
              </p>
              <p className="text-xs text-gray-500">
                {new Date(job.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {(job.status === 'running' || job.status === 'pending') && (
              <span className="text-xs text-gray-500">{job.progress}%</span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteJob.mutate(job.job_id);
              }}
              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
