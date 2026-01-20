'use client';

import { useState } from 'react';
import { Pickaxe, History, Settings, Trash2, Database } from 'lucide-react';
import { AnalysisForm } from '@/components/analysis-form';
import { JobProgress } from '@/components/job-progress';
import { ResultsView } from '@/components/results-view';
import { JobsList } from '@/components/jobs-list';
import { StatusBar } from '@/components/status-bar';
import { useJob, useCacheStats, useClearCache } from '@/lib/hooks';
import type { AnalysisResult } from '@/lib/types';

type View = 'form' | 'progress' | 'results';

export function Dashboard() {
  const [currentView, setCurrentView] = useState<View>('form');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const { data: job } = useJob(currentJobId);
  const { data: cacheStats } = useCacheStats();
  const clearCache = useClearCache();

  const handleJobStarted = (jobId: string) => {
    setCurrentJobId(jobId);
    setCurrentView('progress');
  };

  const handleViewResults = () => {
    if (job?.result) {
      setCurrentResult(job.result as AnalysisResult);
      setCurrentView('results');
    }
  };

  const handleSelectJob = (jobId: string) => {
    setCurrentJobId(jobId);
    setShowHistory(false);
    
    // Check if job is completed
    // The job data will be fetched by useJob hook
  };

  const handleBack = () => {
    setCurrentView('form');
    setCurrentJobId(null);
    setCurrentResult(null);
  };

  // Auto-show results when job completes
  if (job?.status === 'completed' && job.result && currentView === 'progress') {
    // Don't auto-switch, let user click the button
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600 rounded-lg">
                <Pickaxe className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Painminer</h1>
                <p className="text-xs text-gray-500">Extract user pain from Reddit</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <StatusBar />
              
              <button
                onClick={() => setShowHistory(!showHistory)}
                className={`p-2 rounded-lg transition-colors ${
                  showHistory ? 'bg-indigo-100 text-indigo-600' : 'text-gray-500 hover:bg-gray-100'
                }`}
                title="Job History"
              >
                <History className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Main content */}
          <main className="flex-1">
            {currentView === 'form' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  New Analysis
                </h2>
                <AnalysisForm onJobStarted={handleJobStarted} />
              </div>
            )}

            {currentView === 'progress' && currentJobId && (
              <JobProgress jobId={currentJobId} onComplete={handleViewResults} />
            )}

            {currentView === 'results' && currentResult && (
              <ResultsView result={currentResult} onBack={handleBack} />
            )}
          </main>

          {/* Sidebar */}
          {showHistory && (
            <aside className="w-80 shrink-0">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sticky top-8">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Job History
                </h3>
                <JobsList
                  onSelectJob={(jobId) => {
                    handleSelectJob(jobId);
                    // If the job is completed, show results
                    // This will be handled after job data is fetched
                  }}
                  selectedJobId={currentJobId}
                />
                
                {/* Cache stats */}
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    Cache
                  </h4>
                  {cacheStats && (
                    <div className="text-xs text-gray-500 space-y-1 mb-3">
                      <p>Files: {cacheStats.total_files}</p>
                      <p>Size: {cacheStats.total_size_mb?.toFixed(2) || 0} MB</p>
                    </div>
                  )}
                  <button
                    onClick={() => clearCache.mutate()}
                    disabled={clearCache.isPending}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear Cache
                  </button>
                </div>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
