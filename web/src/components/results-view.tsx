'use client';

import { useState } from 'react';
import { 
  Lightbulb, 
  Users, 
  Layers, 
  Smartphone, 
  Database, 
  Bell, 
  TrendingUp,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  MessageSquare,
  BarChart3
} from 'lucide-react';
import type { AnalysisResult, AppIdeaResponse, ClusterResponse } from '@/lib/types';

interface ResultsViewProps {
  result: AnalysisResult;
  onBack: () => void;
}

const complexityColors = {
  XS: 'bg-green-100 text-green-800',
  S: 'bg-yellow-100 text-yellow-800',
  M: 'bg-orange-100 text-orange-800',
};

const complexityLabels = {
  XS: 'Extra Small',
  S: 'Small',
  M: 'Medium',
};

export function ResultsView({ result, onBack }: ResultsViewProps) {
  const [activeTab, setActiveTab] = useState<'ideas' | 'clusters'>('ideas');
  const [expandedIdea, setExpandedIdea] = useState<string | null>(null);
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard
          icon={<MessageSquare className="h-5 w-5" />}
          label="Posts"
          value={result.total_posts}
          color="text-blue-600"
          bg="bg-blue-50"
        />
        <StatCard
          icon={<MessageSquare className="h-5 w-5" />}
          label="Comments"
          value={result.total_comments}
          color="text-purple-600"
          bg="bg-purple-50"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Pain Items"
          value={result.total_pain_items}
          color="text-red-600"
          bg="bg-red-50"
        />
        <StatCard
          icon={<Layers className="h-5 w-5" />}
          label="Clusters"
          value={result.total_clusters}
          color="text-indigo-600"
          bg="bg-indigo-50"
        />
        <StatCard
          icon={<Lightbulb className="h-5 w-5" />}
          label="Ideas"
          value={result.total_ideas}
          color="text-amber-600"
          bg="bg-amber-50"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('ideas')}
          className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'ideas'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            App Ideas ({result.ideas.length})
          </div>
        </button>
        <button
          onClick={() => setActiveTab('clusters')}
          className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'clusters'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Pain Clusters ({result.clusters.length})
          </div>
        </button>
      </div>

      {/* Ideas Tab */}
      {activeTab === 'ideas' && (
        <div className="space-y-4">
          {result.ideas.map((idea, index) => (
            <IdeaCard
              key={index}
              idea={idea}
              index={index}
              isExpanded={expandedIdea === idea.idea_name}
              onToggle={() => setExpandedIdea(
                expandedIdea === idea.idea_name ? null : idea.idea_name
              )}
            />
          ))}
          {result.ideas.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No app ideas were generated. Try adjusting your filters.
            </div>
          )}
        </div>
      )}

      {/* Clusters Tab */}
      {activeTab === 'clusters' && (
        <div className="space-y-4">
          {result.clusters.map((cluster, index) => (
            <ClusterCard
              key={cluster.cluster_id}
              cluster={cluster}
              index={index}
              isExpanded={expandedCluster === cluster.cluster_id}
              onToggle={() => setExpandedCluster(
                expandedCluster === cluster.cluster_id ? null : cluster.cluster_id
              )}
            />
          ))}
        </div>
      )}

      {/* Back button */}
      <div className="pt-4 border-t border-gray-200">
        <button
          onClick={onBack}
          className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium"
        >
          ← Start New Analysis
        </button>
      </div>
    </div>
  );
}

function StatCard({ 
  icon, 
  label, 
  value, 
  color, 
  bg 
}: { 
  icon: React.ReactNode; 
  label: string; 
  value: number; 
  color: string;
  bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-4`}>
      <div className={`${color} mb-2`}>{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}

function IdeaCard({ 
  idea, 
  index, 
  isExpanded, 
  onToggle 
}: { 
  idea: AppIdeaResponse; 
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-100 text-amber-600 font-bold">
            {index + 1}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{idea.idea_name}</h3>
            <p className="text-sm text-gray-500 line-clamp-1">{idea.problem_statement}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${complexityColors[idea.mvp_complexity]}`}>
            {complexityLabels[idea.mvp_complexity]}
          </span>
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          <div className="grid md:grid-cols-2 gap-6 mt-4">
            {/* Left column */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Users className="h-4 w-4" />
                  Target User
                </div>
                <p className="text-gray-600">{idea.target_user}</p>
              </div>

              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Lightbulb className="h-4 w-4" />
                  Core Functions
                </div>
                <ul className="space-y-1">
                  {idea.core_functions.map((func, i) => (
                    <li key={i} className="flex items-start gap-2 text-gray-600">
                      <span className="text-indigo-500 mt-1">•</span>
                      {func}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Smartphone className="h-4 w-4" />
                  Screens
                </div>
                <div className="flex flex-wrap gap-2">
                  {idea.screens.map((screen, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                    >
                      {screen}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Right column */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Database className="h-4 w-4" />
                  Local Data
                </div>
                <ul className="space-y-1">
                  {idea.local_data.map((data, i) => (
                    <li key={i} className="flex items-start gap-2 text-gray-600">
                      <span className="text-green-500 mt-1">•</span>
                      {data}
                    </li>
                  ))}
                </ul>
              </div>

              {idea.minimal_notifications.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Bell className="h-4 w-4" />
                    Notifications
                  </div>
                  <ul className="space-y-1">
                    {idea.minimal_notifications.map((notif, i) => (
                      <li key={i} className="flex items-start gap-2 text-gray-600">
                        <span className="text-purple-500 mt-1">•</span>
                        {notif}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {idea.reddit_evidence && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <BarChart3 className="h-4 w-4" />
                    Reddit Evidence
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-sm">
                    {idea.reddit_evidence.cluster_label && (
                      <p className="text-gray-600">
                        <span className="font-medium">Cluster:</span> {idea.reddit_evidence.cluster_label}
                      </p>
                    )}
                    {idea.reddit_evidence.pain_count && (
                      <p className="text-gray-600">
                        <span className="font-medium">Pain statements:</span> {idea.reddit_evidence.pain_count}
                      </p>
                    )}
                    {idea.reddit_evidence.avg_score && (
                      <p className="text-gray-600">
                        <span className="font-medium">Avg score:</span> {idea.reddit_evidence.avg_score.toFixed(1)}
                      </p>
                    )}
                    {idea.reddit_evidence.top_subreddits && idea.reddit_evidence.top_subreddits.length > 0 && (
                      <p className="text-gray-600">
                        <span className="font-medium">Subreddits:</span> {idea.reddit_evidence.top_subreddits.join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ClusterCard({ 
  cluster, 
  index,
  isExpanded, 
  onToggle 
}: { 
  cluster: ClusterResponse; 
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 font-bold">
            {index + 1}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{cluster.label}</h3>
            <p className="text-sm text-gray-500">
              {cluster.count} items • Avg score: {cluster.avg_score.toFixed(1)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
            {cluster.count} items
          </span>
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          {/* Example texts */}
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Example Pain Statements</h4>
            <div className="space-y-2">
              {cluster.example_texts.map((text, i) => (
                <blockquote
                  key={i}
                  className="pl-3 border-l-2 border-indigo-300 text-gray-600 text-sm italic"
                >
                  "{text}"
                </blockquote>
              ))}
            </div>
          </div>

          {/* Items */}
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Items ({cluster.items.length} shown)
            </h4>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {cluster.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg text-sm"
                >
                  <div className="flex-1">
                    <p className="text-gray-700">{item.text}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>r/{item.subreddit}</span>
                      <span>• Score: {item.score}</span>
                      <span>• {item.source_type}</span>
                    </div>
                  </div>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:text-indigo-800"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
