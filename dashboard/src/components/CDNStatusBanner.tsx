'use client';

import { useState, useEffect, useCallback } from 'react';

interface FileProgress {
  status: string;
  percent: number;
  loaded_bytes: number;
  total_bytes: number;
  error: string | null;
}

interface CDNStatus {
  state: 'idle' | 'loading' | 'completed' | 'failed' | 'partial';
  version: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_patterns: number;
  error: string | null;
  files: Record<string, FileProgress>;
  overall_percent: number;
}

const POLL_INTERVAL = 5000; // 5 seconds while loading

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function CDNStatusBanner() {
  const [status, setStatus] = useState<CDNStatus | null>(null);
  const [isMinimized, setIsMinimized] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/strike/cdn/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.error('CDN status fetch failed:', e);
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    // Poll while loading
    const interval = setInterval(() => {
      if (status?.state === 'loading') {
        fetchStatus();
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchStatus, status?.state]);

  // Don't show if completed successfully
  if (!status || status.state === 'completed') {
    return null;
  }

  // Don't show if idle
  if (status.state === 'idle') {
    return null;
  }

  const isLoading = status.state === 'loading';
  const isFailed = status.state === 'failed';
  const isPartial = status.state === 'partial';

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 rounded-lg shadow-lg backdrop-blur-sm
        ${isFailed ? 'bg-red-500/90' : isPartial ? 'bg-yellow-500/90' : 'bg-blue-500/90'}
        text-white max-w-md transition-all duration-300 ${isMinimized ? 'w-auto' : 'w-96'}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer"
        onClick={() => setIsMinimized(!isMinimized)}
      >
        <div className="flex items-center gap-2">
          {isLoading && (
            <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
          )}
          {isFailed && <span>⚠️</span>}
          {isPartial && <span>📂</span>}
          <span className="font-medium">
            {isLoading ? 'Loading AI Signatures...' : isFailed ? 'CDN Failed' : 'Using Local Cache'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && (
            <span className="text-sm font-mono">{status.overall_percent}%</span>
          )}
          <button className="text-white/70 hover:text-white">
            {isMinimized ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Expanded content */}
      {!isMinimized && (
        <div className="px-3 pb-3 border-t border-white/20">
          {/* Progress bar */}
          {isLoading && (
            <div className="mt-2 bg-white/20 rounded-full h-2 overflow-hidden">
              <div
                className="bg-white h-full transition-all duration-300"
                style={{ width: `${status.overall_percent}%` }}
              />
            </div>
          )}

          {/* Files list */}
          <div className="mt-3 space-y-1 text-sm">
            {Object.entries(status.files || {}).map(([name, file]) => (
              <div key={name} className="flex items-center justify-between">
                <span className="truncate flex-1">
                  {file.status === 'done' && '✓ '}
                  {file.status === 'loading' && '↓ '}
                  {file.status === 'error' && '✗ '}
                  {name.replace('jailbreaks_', 'jb_')}
                </span>
                <span className="ml-2 font-mono text-xs">
                  {file.status === 'loading' ? (
                    `${formatBytes(file.loaded_bytes)} / ${formatBytes(file.total_bytes)}`
                  ) : file.status === 'done' ? (
                    formatBytes(file.total_bytes)
                  ) : file.status === 'error' ? (
                    <span className="text-red-200">{file.error}</span>
                  ) : (
                    'pending'
                  )}
                </span>
              </div>
            ))}
          </div>

          {/* Total patterns */}
          {status.total_patterns > 0 && (
            <div className="mt-2 pt-2 border-t border-white/20 text-sm">
              Total patterns: <strong>{status.total_patterns.toLocaleString()}</strong>
            </div>
          )}

          {/* Error message */}
          {status.error && (
            <div className="mt-2 text-sm text-red-200">
              Error: {status.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
