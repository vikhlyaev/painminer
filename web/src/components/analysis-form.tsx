'use client';

import { useState, useEffect } from 'react';
import { Plus, X, Play, Loader2, ChevronDown, ChevronUp, Globe } from 'lucide-react';
import { useSubredditPresets, usePhrasePresets, useStartAnalysis } from '@/lib/hooks';
import type { SubredditInput, AnalysisRequest, RedditCredentials, FiltersInput, ClusteringInput, NetworkConfig, ProxyConfig } from '@/lib/types';

interface AnalysisFormProps {
  onJobStarted: (jobId: string) => void;
}

const DEFAULT_SUBREDDIT: SubredditInput = {
  name: '',
  period_days: 30,
  min_upvotes: 10,
  max_posts: 100,
  max_comments_per_post: 30,
};

const DEFAULT_FILTERS: FiltersInput = {
  include_phrases: [
    'I struggle', 'I keep forgetting', 'I wish', 'How do you',
    'Is there an app', 'Anyone else'
  ],
  exclude_phrases: ['politics', 'rant'],
  min_pain_length: 12,
};

const DEFAULT_CLUSTERING: ClusteringInput = {
  method: 'tfidf_kmeans',
  k_min: 5,
  k_max: 20,
  random_state: 42,
};

const DEFAULT_PROXY: ProxyConfig = {
  enabled: false,
  mode: 'single',
  single_http: '',
  single_https: '',
  pool: [],
  rotate_every_requests: 25,
};

const DEFAULT_NETWORK: NetworkConfig = {
  timeout_sec: 20,
  proxy: DEFAULT_PROXY,
};

export function AnalysisForm({ onJobStarted }: AnalysisFormProps) {
  const { data: subredditPresets } = useSubredditPresets();
  const { data: phrasePresets } = usePhrasePresets();
  const startAnalysis = useStartAnalysis();

  const [subreddits, setSubreddits] = useState<SubredditInput[]>([{ ...DEFAULT_SUBREDDIT }]);
  const [credentials, setCredentials] = useState<RedditCredentials>({
    client_id: '',
    client_secret: '',
    username: '',
    password: '',
    user_agent: 'painminer-web/0.1',
  });
  const [filters, setFilters] = useState<FiltersInput>(DEFAULT_FILTERS);
  const [clustering, setClustering] = useState<ClusteringInput>(DEFAULT_CLUSTERING);
  const [network, setNetwork] = useState<NetworkConfig>(DEFAULT_NETWORK);
  const [useCache, setUseCache] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showProxy, setShowProxy] = useState(false);
  const [newIncludePhrase, setNewIncludePhrase] = useState('');
  const [newExcludePhrase, setNewExcludePhrase] = useState('');
  const [newProxyUrl, setNewProxyUrl] = useState('');

  // Load credentials from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('reddit_credentials');
    if (saved) {
      try {
        setCredentials(JSON.parse(saved));
      } catch {
        // Ignore
      }
    }
  }, []);

  // Save credentials to localStorage
  const saveCredentials = () => {
    localStorage.setItem('reddit_credentials', JSON.stringify(credentials));
  };

  const addSubreddit = (name: string = '') => {
    setSubreddits([...subreddits, { ...DEFAULT_SUBREDDIT, name }]);
  };

  const removeSubreddit = (index: number) => {
    setSubreddits(subreddits.filter((_, i) => i !== index));
  };

  const updateSubreddit = (index: number, field: keyof SubredditInput, value: string | number) => {
    const updated = [...subreddits];
    updated[index] = { ...updated[index], [field]: value };
    setSubreddits(updated);
  };

  const addIncludePhrase = () => {
    if (newIncludePhrase.trim() && !filters.include_phrases.includes(newIncludePhrase.trim())) {
      setFilters({
        ...filters,
        include_phrases: [...filters.include_phrases, newIncludePhrase.trim()],
      });
      setNewIncludePhrase('');
    }
  };

  const removeIncludePhrase = (phrase: string) => {
    setFilters({
      ...filters,
      include_phrases: filters.include_phrases.filter(p => p !== phrase),
    });
  };

  const addExcludePhrase = () => {
    if (newExcludePhrase.trim() && !filters.exclude_phrases.includes(newExcludePhrase.trim())) {
      setFilters({
        ...filters,
        exclude_phrases: [...filters.exclude_phrases, newExcludePhrase.trim()],
      });
      setNewExcludePhrase('');
    }
  };

  const addProxyToPool = () => {
    if (newProxyUrl.trim() && !network.proxy.pool.includes(newProxyUrl.trim())) {
      setNetwork({
        ...network,
        proxy: {
          ...network.proxy,
          pool: [...network.proxy.pool, newProxyUrl.trim()],
        },
      });
      setNewProxyUrl('');
    }
  };

  const removeProxyFromPool = (url: string) => {
    setNetwork({
      ...network,
      proxy: {
        ...network.proxy,
        pool: network.proxy.pool.filter(p => p !== url),
      },
    });
  };

  const removeExcludePhrase = (phrase: string) => {
    setFilters({
      ...filters,
      exclude_phrases: filters.exclude_phrases.filter(p => p !== phrase),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate
    const validSubreddits = subreddits.filter(s => s.name.trim());
    if (validSubreddits.length === 0) {
      alert('Please add at least one subreddit');
      return;
    }
    
    if (!credentials.client_id || !credentials.client_secret) {
      alert('Please enter Reddit API credentials');
      return;
    }

    saveCredentials();

    const request: AnalysisRequest = {
      subreddits: validSubreddits,
      reddit: credentials,
      filters,
      clustering,
      network,
      use_cache: useCache,
    };

    try {
      const job = await startAnalysis.mutateAsync(request);
      onJobStarted(job.job_id);
    } catch (error) {
      console.error('Failed to start analysis:', error);
      alert('Failed to start analysis. Please check the API connection.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Subreddits */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-gray-900">Subreddits</h3>
          <button
            type="button"
            onClick={() => addSubreddit()}
            className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
        
        {/* Preset subreddits */}
        {subredditPresets && (
          <div className="mb-4 flex flex-wrap gap-2">
            {subredditPresets.map((preset) => (
              <button
                key={preset.name}
                type="button"
                onClick={() => {
                  if (!subreddits.some(s => s.name === preset.name)) {
                    addSubreddit(preset.name);
                  }
                }}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
                title={preset.description}
              >
                r/{preset.name}
              </button>
            ))}
          </div>
        )}
        
        <div className="space-y-3">
          {subreddits.map((sub, index) => (
            <div key={index} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg">
              <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="col-span-2 md:col-span-1">
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Subreddit
                  </label>
                  <input
                    type="text"
                    value={sub.name}
                    onChange={(e) => updateSubreddit(index, 'name', e.target.value)}
                    placeholder="productivity"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Period (days)
                  </label>
                  <input
                    type="number"
                    value={sub.period_days}
                    onChange={(e) => updateSubreddit(index, 'period_days', parseInt(e.target.value) || 30)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Min Upvotes
                  </label>
                  <input
                    type="number"
                    value={sub.min_upvotes}
                    onChange={(e) => updateSubreddit(index, 'min_upvotes', parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Max Posts
                  </label>
                  <input
                    type="number"
                    value={sub.max_posts}
                    onChange={(e) => updateSubreddit(index, 'max_posts', parseInt(e.target.value) || 100)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              {subreddits.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeSubreddit(index)}
                  className="mt-6 p-1 text-gray-400 hover:text-red-500"
                >
                  <X className="h-5 w-5" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Reddit Credentials */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">Reddit API Credentials</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Client ID
            </label>
            <input
              type="text"
              value={credentials.client_id}
              onChange={(e) => setCredentials({ ...credentials, client_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Your Reddit app client ID"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Client Secret
            </label>
            <input
              type="password"
              value={credentials.client_secret}
              onChange={(e) => setCredentials({ ...credentials, client_secret: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Your Reddit app client secret"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              type="text"
              value={credentials.username}
              onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Reddit username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Reddit password"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Credentials are saved locally in your browser and never sent to third parties.
        </p>
      </div>

      {/* Include/Exclude Phrases */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">Filters</h3>
        
        <div className="space-y-4">
          {/* Include phrases */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Include phrases (pain indicators)
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {filters.include_phrases.map((phrase) => (
                <span
                  key={phrase}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-sm rounded-full"
                >
                  {phrase}
                  <button
                    type="button"
                    onClick={() => removeIncludePhrase(phrase)}
                    className="hover:text-green-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newIncludePhrase}
                onChange={(e) => setNewIncludePhrase(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addIncludePhrase())}
                placeholder="Add phrase..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={addIncludePhrase}
                className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                <Plus className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Exclude phrases */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Exclude phrases (filter out)
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {filters.exclude_phrases.map((phrase) => (
                <span
                  key={phrase}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-800 text-sm rounded-full"
                >
                  {phrase}
                  <button
                    type="button"
                    onClick={() => removeExcludePhrase(phrase)}
                    className="hover:text-red-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newExcludePhrase}
                onChange={(e) => setNewExcludePhrase(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addExcludePhrase())}
                placeholder="Add phrase..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={addExcludePhrase}
                className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                <Plus className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Proxy Settings */}
      <div>
        <button
          type="button"
          onClick={() => setShowProxy(!showProxy)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          {showProxy ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          <Globe className="h-4 w-4" />
          Proxy Settings
          {network.proxy.enabled && (
            <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full">
              Enabled
            </span>
          )}
        </button>

        {showProxy && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="proxyEnabled"
                checked={network.proxy.enabled}
                onChange={(e) => setNetwork({
                  ...network,
                  proxy: { ...network.proxy, enabled: e.target.checked }
                })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label htmlFor="proxyEnabled" className="text-sm text-gray-700">
                Enable proxy for Reddit API requests
              </label>
            </div>

            {network.proxy.enabled && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Proxy Mode
                  </label>
                  <div className="flex gap-4">
                    <label className="inline-flex items-center">
                      <input
                        type="radio"
                        value="single"
                        checked={network.proxy.mode === 'single'}
                        onChange={(e) => setNetwork({
                          ...network,
                          proxy: { ...network.proxy, mode: 'single' }
                        })}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">Single Proxy</span>
                    </label>
                    <label className="inline-flex items-center">
                      <input
                        type="radio"
                        value="pool"
                        checked={network.proxy.mode === 'pool'}
                        onChange={(e) => setNetwork({
                          ...network,
                          proxy: { ...network.proxy, mode: 'pool' }
                        })}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">Proxy Pool (rotate)</span>
                    </label>
                  </div>
                </div>

                {network.proxy.mode === 'single' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        HTTP Proxy
                      </label>
                      <input
                        type="text"
                        value={network.proxy.single_http}
                        onChange={(e) => setNetwork({
                          ...network,
                          proxy: { ...network.proxy, single_http: e.target.value }
                        })}
                        placeholder="http://user:pass@proxy:8080"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        HTTPS Proxy
                      </label>
                      <input
                        type="text"
                        value={network.proxy.single_https}
                        onChange={(e) => setNetwork({
                          ...network,
                          proxy: { ...network.proxy, single_https: e.target.value }
                        })}
                        placeholder="http://user:pass@proxy:8080"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Proxy Pool
                      </label>
                      {network.proxy.pool.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                          {network.proxy.pool.map((url, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full max-w-xs truncate"
                              title={url}
                            >
                              <span className="truncate">{url}</span>
                              <button
                                type="button"
                                onClick={() => removeProxyFromPool(url)}
                                className="hover:text-blue-600 flex-shrink-0"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newProxyUrl}
                          onChange={(e) => setNewProxyUrl(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addProxyToPool())}
                          placeholder="http://user:pass@proxy:8080 or socks5://..."
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                        />
                        <button
                          type="button"
                          onClick={addProxyToPool}
                          className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                          <Plus className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Rotate every N requests
                      </label>
                      <input
                        type="number"
                        value={network.proxy.rotate_every_requests}
                        onChange={(e) => setNetwork({
                          ...network,
                          proxy: { ...network.proxy, rotate_every_requests: parseInt(e.target.value) || 25 }
                        })}
                        min={1}
                        className="w-32 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                )}

                <p className="text-xs text-gray-500">
                  Proxy helps bypass rate limits or access Reddit from restricted regions. 
                  Supports HTTP, HTTPS, and SOCKS5 protocols.
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Advanced Options */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          Advanced Options
        </button>
        
        {showAdvanced && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Clustering Method
                </label>
                <select
                  value={clustering.method}
                  onChange={(e) => setClustering({ ...clustering, method: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="tfidf_kmeans">TF-IDF + KMeans</option>
                  <option value="hash">Simple Hash</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Min Clusters (K)
                </label>
                <input
                  type="number"
                  value={clustering.k_min}
                  onChange={(e) => setClustering({ ...clustering, k_min: parseInt(e.target.value) || 5 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Clusters (K)
                </label>
                <input
                  type="number"
                  value={clustering.k_max}
                  onChange={(e) => setClustering({ ...clustering, k_max: parseInt(e.target.value) || 20 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Min Pain Length
                </label>
                <input
                  type="number"
                  value={filters.min_pain_length}
                  onChange={(e) => setFilters({ ...filters, min_pain_length: parseInt(e.target.value) || 12 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="useCache"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label htmlFor="useCache" className="text-sm text-gray-700">
                Use cached Reddit data (faster, but may be stale)
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={startAnalysis.isPending}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {startAnalysis.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <Play className="h-5 w-5" />
              Start Analysis
            </>
          )}
        </button>
      </div>
    </form>
  );
}
