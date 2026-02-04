'use client'

import { useState } from 'react'
import { GitCompare, ArrowRight, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface CompareResult {
  risk_level: string
  score: number
  verdict: string
  engines_triggered: string[]
}

interface CompareModeProps {
  selectedEngines: string[]
}

export default function CompareMode({ selectedEngines }: CompareModeProps) {
  const [leftText, setLeftText] = useState('')
  const [rightText, setRightText] = useState('')
  const [leftResult, setLeftResult] = useState<CompareResult | null>(null)
  const [rightResult, setRightResult] = useState<CompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function analyze(text: string): Promise<CompareResult | null> {
    try {
      const res = await fetch('/api/brain/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          engines: selectedEngines.length > 0 ? selectedEngines : undefined,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        return {
          risk_level: data.risk_level || 'unknown',
          score: data.score || data.risk_score || 0,
          verdict: data.verdict || 'N/A',
          engines_triggered: data.engines_triggered || [],
        }
      }
    } catch { /* ignore API errors */ }
    return null
  }

  async function runCompare() {
    if (!leftText.trim() || !rightText.trim()) return

    setLoading(true)
    setError(null)
    setLeftResult(null)
    setRightResult(null)

    try {
      const [left, right] = await Promise.all([
        analyze(leftText),
        analyze(rightText),
      ])

      if (left && right) {
        setLeftResult(left)
        setRightResult(right)
      } else {
        setError('Failed to analyze one or both texts')
      }
    } catch {
      setError('Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const riskColors: Record<string, string> = {
    low: 'text-green-400 bg-green-500/20 border-green-500/30',
    medium: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30',
    high: 'text-orange-400 bg-orange-500/20 border-orange-500/30',
    critical: 'text-red-400 bg-red-500/20 border-red-500/30',
  }

  const getDelta = () => {
    if (!leftResult || !rightResult) return null
    return rightResult.score - leftResult.score
  }

  const delta = getDelta()

  return (
    <div className="space-y-4">
      {/* Input Areas */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm text-gray-400 mb-2 block">Original Text</label>
          <textarea
            value={leftText}
            onChange={(e) => setLeftText(e.target.value)}
            placeholder="Enter original prompt..."
            className="w-full h-32 bg-gray-900/50 border border-gray-700 rounded-xl p-3 text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-purple-500/50"
          />
        </div>
        <div>
          <label className="text-sm text-gray-400 mb-2 block">Modified Text</label>
          <textarea
            value={rightText}
            onChange={(e) => setRightText(e.target.value)}
            placeholder="Enter modified prompt..."
            className="w-full h-32 bg-gray-900/50 border border-gray-700 rounded-xl p-3 text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Compare Button */}
      <div className="flex justify-center">
        <button
          onClick={runCompare}
          disabled={loading || !leftText.trim() || !rightText.trim()}
          className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-600 to-cyan-600 rounded-xl text-white font-medium hover:from-purple-500 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <GitCompare className="w-5 h-5" />
          )}
          {loading ? 'Comparing...' : 'Compare'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm text-center">
          {error}
        </div>
      )}

      {/* Results */}
      {leftResult && rightResult && (
        <div className="space-y-4">
          {/* Delta Summary */}
          <div className="flex items-center justify-center gap-4 p-4 bg-gray-900/50 rounded-xl">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">{leftResult.score}</div>
              <div className="text-xs text-gray-500">Original</div>
            </div>
            <ArrowRight className="w-6 h-6 text-gray-500" />
            <div className="text-center">
              <div className="text-2xl font-bold text-cyan-400">{rightResult.score}</div>
              <div className="text-xs text-gray-500">Modified</div>
            </div>
            <div className={`flex items-center gap-1 px-3 py-1.5 rounded-lg ${
              delta === 0 
                ? 'bg-gray-500/20 text-gray-400' 
                : delta! > 0 
                  ? 'bg-red-500/20 text-red-400' 
                  : 'bg-green-500/20 text-green-400'
            }`}>
              {delta === 0 ? (
                <Minus className="w-4 h-4" />
              ) : delta! > 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span className="font-medium">
                {delta === 0 ? 'No change' : delta! > 0 ? `+${delta}` : delta}
              </span>
            </div>
          </div>

          {/* Side by Side Results */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { result: leftResult, label: 'Original', color: 'purple' },
              { result: rightResult, label: 'Modified', color: 'cyan' },
            ].map(({ result, label, color }) => (
              <div key={label} className={`p-4 rounded-xl border ${riskColors[result.risk_level] || 'border-gray-700'}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-sm font-medium text-${color}-400`}>{label}</span>
                  <span className={`px-2 py-0.5 rounded text-xs uppercase ${riskColors[result.risk_level]}`}>
                    {result.risk_level}
                  </span>
                </div>
                <div className="text-sm text-gray-400">
                  <div>Verdict: <span className="text-white">{result.verdict}</span></div>
                  <div>Engines: <span className="text-white">{result.engines_triggered.length}</span></div>
                  {result.engines_triggered.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {result.engines_triggered.slice(0, 3).map(e => (
                        <span key={e} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">
                          {e}
                        </span>
                      ))}
                      {result.engines_triggered.length > 3 && (
                        <span className="text-xs text-gray-500">+{result.engines_triggered.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
