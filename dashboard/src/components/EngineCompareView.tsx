'use client'

/**
 * Engine Compare View
 *
 * Side-by-side comparison of Qwen3-Guard and Foundation-sec analysis
 */

import { useState } from 'react'
import {
  Send,
  Loader2,
  Shield,
  Brain,
  ArrowRight,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { ReasoningViewer } from './ReasoningViewer'

interface QwenResult {
  level: 'safe' | 'controversial' | 'unsafe'
  categories: string[]
  risk_score: number
}

interface FoundationResult {
  analysis_type: string
  reasoning: {
    thinking: string
    conclusion: string
    confidence: number
  }
  mitre_mappings: Array<{
    technique_id: string
    technique_name: string
    tactic: string
    confidence: number
  }>
  risk_score: number
  recommendations: string[]
  latency_ms: number
}

interface CompareResults {
  qwen?: { engine: string; result: QwenResult; latency_ms: number }
  foundation?: { engine: string; result: FoundationResult }
}

export function EngineCompareView() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<CompareResults | null>(null)

  const runComparison = async () => {
    if (!input.trim()) return

    setLoading(true)
    setResults(null)

    try {
      // Run both analyses in parallel
      const [qwenRes, foundationRes] = await Promise.all([
        fetch('/api/brain/engines/qwen-guard/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: input }),
        }),
        fetch('/api/brain/engines/foundation-sec/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: input,
            analysis_type: 'threat_model',
            include_mitre: true,
          }),
        }),
      ])

      const qwen = qwenRes.ok ? await qwenRes.json() : null
      const foundation = foundationRes.ok ? await foundationRes.json() : null

      setResults({ qwen, foundation })
    } catch (error) {
      console.error('Comparison failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'safe':
        return <CheckCircle className="w-5 h-5 text-emerald-400" />
      case 'controversial':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />
      case 'unsafe':
        return <XCircle className="w-5 h-5 text-red-400" />
      default:
        return null
    }
  }

  const getLevelBg = (level: string) => {
    switch (level) {
      case 'safe':
        return 'bg-emerald-500/20 border-emerald-500/30'
      case 'controversial':
        return 'bg-yellow-500/20 border-yellow-500/30'
      case 'unsafe':
        return 'bg-red-500/20 border-red-500/30'
      default:
        return 'bg-gray-500/20 border-gray-500/30'
    }
  }

  return (
    <div className="space-y-6">
      {/* Input */}
      <div className="bg-[#1f2937] rounded-xl border border-[#374151] p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-5 h-5 text-purple-400" />
          <h3 className="font-semibold">Compare Engines</h3>
        </div>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter text to analyze with both engines..."
          className="w-full bg-[#111827] border border-[#374151] rounded-lg p-3 
                     text-gray-200 placeholder-gray-500 resize-none h-32
                     focus:outline-none focus:ring-2 focus:ring-purple-500/50"
        />

        <div className="flex justify-end mt-3">
          <button
            onClick={runComparison}
            disabled={loading || !input.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-purple-500 
                       hover:bg-purple-600 disabled:bg-gray-600 disabled:cursor-not-allowed
                       rounded-lg font-medium transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Compare
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Qwen3-Guard Result */}
          <div className="bg-[#111827] rounded-xl border border-[#374151]">
            <div className="p-4 border-b border-[#374151]">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-400" />
                <h3 className="font-semibold">Qwen3-Guard</h3>
                {results.qwen && (
                  <span className="text-xs text-gray-500">
                    {results.qwen.latency_ms}ms
                  </span>
                )}
              </div>
            </div>

            <div className="p-4">
              {results.qwen ? (
                <div className="space-y-4">
                  {/* Level */}
                  <div
                    className={`rounded-lg p-3 border ${getLevelBg(
                      results.qwen.result.level
                    )}`}
                  >
                    <div className="flex items-center gap-2">
                      {getLevelIcon(results.qwen.result.level)}
                      <span className="font-semibold capitalize">
                        {results.qwen.result.level}
                      </span>
                      <ArrowRight className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-400">
                        Risk: {results.qwen.result.risk_score}/100
                      </span>
                    </div>
                  </div>

                  {/* Categories */}
                  {results.qwen.result.categories.length > 0 && (
                    <div>
                      <p className="text-sm text-gray-500 mb-2">
                        Detected Categories:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {results.qwen.result.categories.map((cat, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 text-xs bg-red-500/20 
                                       text-red-400 rounded-lg border border-red-500/30"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {results.qwen.result.categories.length === 0 && (
                    <p className="text-gray-400 text-sm">
                      No safety concerns detected.
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-red-400">Failed to get Qwen result</p>
              )}
            </div>
          </div>

          {/* Foundation-sec Result */}
          <div className="bg-[#111827] rounded-xl border border-[#374151]">
            <div className="p-4 border-b border-[#374151]">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-400" />
                <h3 className="font-semibold">Foundation-sec</h3>
                {results.foundation && (
                  <span className="text-xs text-gray-500">
                    {results.foundation.result.latency_ms}ms
                  </span>
                )}
              </div>
            </div>

            <div className="p-4">
              {results.foundation ? (
                <ReasoningViewer result={results.foundation.result} />
              ) : (
                <p className="text-red-400">Failed to get Foundation result</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Help Text */}
      {!results && !loading && (
        <div className="text-center py-8 text-gray-500">
          <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Enter text above to compare analysis from both engines</p>
          <p className="text-sm mt-1">
            Qwen3-Guard = Fast classification • Foundation-sec = Deep reasoning
          </p>
        </div>
      )}
    </div>
  )
}

export default EngineCompareView
