'use client'

import { useState, useRef } from 'react'
import { Upload, FileText, Play, Download, X, Loader2 } from 'lucide-react'

interface BatchResult {
  text: string
  risk_level: string
  score: number
  verdict: string
  engines_triggered: string[]
}

interface BatchAnalyzerProps {
  selectedEngines: string[]
}

export default function BatchAnalyzer({ selectedEngines }: BatchAnalyzerProps) {
  const [items, setItems] = useState<string[]>([])
  const [results, setResults] = useState<BatchResult[]>([])
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string
        
        if (file.name.endsWith('.json')) {
          const data = JSON.parse(content)
          let texts: string[] = []
          
          if (Array.isArray(data)) {
            texts = data.map(d => {
              if (typeof d === 'string') return d
              if (d && typeof d === 'object') {
                return d.text || d.prompt || d.content || d.message || JSON.stringify(d)
              }
              return String(d)
            })
          } else if (typeof data === 'object' && data !== null) {
            // Single object or object with items array
            if (data.items && Array.isArray(data.items)) {
              texts = data.items.map((d: any) => d.text || d.prompt || String(d))
            } else {
              texts = [data.text || data.prompt || JSON.stringify(data)]
            }
          } else {
            texts = [String(data)]
          }
          
          setItems(texts.filter(t => t && t.trim()).slice(0, 100))
        } else if (file.name.endsWith('.csv')) {
          const lines = content.split('\n').filter(l => l.trim())
          // Skip header if present
          const startIdx = lines[0]?.toLowerCase().includes('text') ? 1 : 0
          const parsed = lines.slice(startIdx, 101).map(l => {
            // Handle quoted CSV values
            const trimmed = l.trim()
            if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
              return trimmed.slice(1, -1).replace(/""/g, '"')
            }
            return trimmed
          })
          setItems(parsed.filter(t => t))
        } else {
          // Plain text, one per line
          setItems(content.split('\n').filter(l => l.trim()).slice(0, 100))
        }
        setError(null)
        setResults([])
      } catch (err) {
        setError('Failed to parse file: ' + (err as Error).message)
      }
    }
    reader.readAsText(file)
  }

  async function runBatch() {
    if (items.length === 0) return
    
    setProcessing(true)
    setProgress(0)
    setResults([])
    setError(null)

    const batchResults: BatchResult[] = new Array(items.length).fill(null)
    let completed = 0

    // Process in parallel batches of 3 for speed
    const BATCH_SIZE = 3
    const TIMEOUT_MS = 10000

    for (let i = 0; i < items.length; i += BATCH_SIZE) {
      const chunk = items.slice(i, i + BATCH_SIZE)
      
      await Promise.all(chunk.map(async (text, j) => {
        const idx = i + j
        try {
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)
          
          const res = await fetch('/api/brain/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text,
              engines: selectedEngines.length > 0 ? selectedEngines : undefined,
            }),
            signal: controller.signal,
          })
          
          clearTimeout(timeoutId)

          if (res.ok) {
            const data = await res.json()
            batchResults[idx] = {
              text: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
              risk_level: data.risk_level || 'unknown',
              score: data.score || data.risk_score || 0,
              verdict: data.verdict || 'N/A',
              engines_triggered: data.engines_triggered || [],
            }
          } else {
            batchResults[idx] = {
              text: text.substring(0, 50) + '...',
              risk_level: 'error',
              score: 0,
              verdict: 'ERROR',
              engines_triggered: [],
            }
          }
        } catch {
          batchResults[idx] = {
            text: text.substring(0, 50) + '...',
            risk_level: 'timeout',
            score: 0,
            verdict: 'TIMEOUT',
            engines_triggered: [],
          }
        }
        
        completed++
        setProgress(Math.round((completed / items.length) * 100))
        setResults(batchResults.filter(r => r !== null) as BatchResult[])
      }))
    }

    setProcessing(false)
  }

  function exportResults() {
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `batch_results_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  function clear() {
    setItems([])
    setResults([])
    setProgress(0)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const riskColors: Record<string, string> = {
    low: 'text-green-400 bg-green-500/20',
    medium: 'text-yellow-400 bg-yellow-500/20',
    high: 'text-orange-400 bg-orange-500/20',
    critical: 'text-red-400 bg-red-500/20',
    error: 'text-gray-400 bg-gray-500/20',
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div 
        className="border-2 border-dashed border-gray-700 rounded-xl p-6 text-center hover:border-purple-500/50 transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,.csv,.txt"
          onChange={handleFileUpload}
          className="hidden"
        />
        <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">
          Drop CSV, JSON, or TXT file here (max 100 items)
        </p>
        <p className="text-gray-500 text-xs mt-1">
          CSV format: one text per line or "text" column
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Items Preview */}
      {items.length > 0 && (
        <div className="bg-gray-900/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-gray-400">
              <FileText className="w-4 h-4 inline mr-1" />
              {items.length} items loaded
            </span>
            <div className="flex gap-2">
              <button
                onClick={clear}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4 inline mr-1" />
                Clear
              </button>
              <button
                onClick={runBatch}
                disabled={processing}
                className="px-4 py-1.5 bg-purple-500/20 text-purple-400 rounded-lg text-sm hover:bg-purple-500/30 disabled:opacity-50 transition-colors"
              >
                {processing ? (
                  <Loader2 className="w-4 h-4 inline mr-1 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 inline mr-1" />
                )}
                {processing ? `${progress}%` : 'Run Batch'}
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {processing && (
            <div className="w-full bg-gray-800 rounded-full h-2 mb-3">
              <div 
                className="bg-purple-500 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}

          {/* Preview first 3 items */}
          <div className="space-y-1 text-xs text-gray-500">
            {items.slice(0, 3).map((item, i) => (
              <div key={i} className="truncate">{item}</div>
            ))}
            {items.length > 3 && <div>... and {items.length - 3} more</div>}
          </div>
        </div>
      )}

      {/* Results Table */}
      {results.length > 0 && (
        <div className="bg-gray-900/50 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b border-gray-800">
            <span className="text-sm text-gray-400">Results</span>
            <button
              onClick={exportResults}
              className="px-3 py-1.5 text-sm text-green-400 hover:text-green-300 transition-colors"
            >
              <Download className="w-4 h-4 inline mr-1" />
              Export JSON
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50 sticky top-0">
                <tr className="text-left text-gray-400">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Text</th>
                  <th className="px-3 py-2">Risk</th>
                  <th className="px-3 py-2">Score</th>
                  <th className="px-3 py-2">Engines</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-3 py-2 text-gray-500">{i + 1}</td>
                    <td className="px-3 py-2 text-gray-300 max-w-xs truncate">{r.text}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${riskColors[r.risk_level] || riskColors.error}`}>
                        {r.risk_level}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-300">{r.score}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs">{r.engines_triggered.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
