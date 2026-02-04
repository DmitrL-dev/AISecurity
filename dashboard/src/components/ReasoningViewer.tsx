'use client'

/**
 * Reasoning Viewer
 *
 * Displays Foundation-sec reasoning traces with syntax highlighting
 */

import { useState } from 'react'
import {
  Brain,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ShieldCheck,
  Target,
  Lightbulb,
  Copy,
  Check,
} from 'lucide-react'

interface MitreMapping {
  technique_id: string
  technique_name: string
  tactic: string
  confidence: number
}

interface ReasoningTrace {
  thinking: string
  conclusion: string
  confidence: number
}

interface AnalysisResult {
  analysis_type: string
  reasoning: ReasoningTrace
  mitre_mappings: MitreMapping[]
  risk_score: number
  recommendations: string[]
  latency_ms: number
}

interface ReasoningViewerProps {
  result: AnalysisResult
  showRaw?: boolean
}

export function ReasoningViewer({ result, showRaw: _showRaw = false }: ReasoningViewerProps) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const getRiskColor = (score: number) => {
    if (score >= 75) return 'text-red-400 bg-red-500/20'
    if (score >= 50) return 'text-yellow-400 bg-yellow-500/20'
    return 'text-emerald-400 bg-emerald-500/20'
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(result.reasoning.conclusion)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Risk Score Banner */}
      <div className={`rounded-lg p-3 ${getRiskColor(result.risk_score)}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-semibold">Risk Score: {result.risk_score.toFixed(0)}/100</span>
          </div>
          <span className="text-sm opacity-80">
            {result.latency_ms.toFixed(0)}ms • {result.analysis_type.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Conclusion */}
      <div className="bg-[#1f2937] rounded-lg border border-[#374151]">
        <div className="p-4 border-b border-[#374151]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-purple-400" />
              <h4 className="font-semibold">Conclusion</h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                Confidence: {(result.reasoning.confidence * 100).toFixed(0)}%
              </span>
              <button
                onClick={handleCopy}
                className="p-1 rounded hover:bg-[#374151] transition-colors"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>
        </div>
        <div className="p-4">
          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
            {result.reasoning.conclusion}
          </p>
        </div>
      </div>

      {/* Thinking (Collapsible) */}
      {result.reasoning.thinking && (
        <div className="bg-[#1f2937] rounded-lg border border-[#374151]">
          <button
            onClick={() => setThinkingExpanded(!thinkingExpanded)}
            className="w-full p-4 flex items-center justify-between hover:bg-[#374151]/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-blue-400" />
              <h4 className="font-semibold">Reasoning Trace</h4>
            </div>
            {thinkingExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          {thinkingExpanded && (
            <div className="p-4 border-t border-[#374151]">
              <pre className="text-sm text-gray-400 whitespace-pre-wrap font-mono">
                {result.reasoning.thinking}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* MITRE ATT&CK Mappings */}
      {result.mitre_mappings.length > 0 && (
        <div className="bg-[#1f2937] rounded-lg border border-[#374151]">
          <div className="p-4 border-b border-[#374151]">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-red-400" />
              <h4 className="font-semibold">MITRE ATT&CK Techniques</h4>
            </div>
          </div>
          <div className="p-4 space-y-2">
            {result.mitre_mappings.map((mapping, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded-lg bg-red-500/10 border border-red-500/20"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-red-400">
                    {mapping.technique_id}
                  </span>
                  <span className="text-gray-300">{mapping.technique_name}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-500">{mapping.tactic}</span>
                  <span className="text-red-400">
                    {(mapping.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <div className="bg-[#1f2937] rounded-lg border border-[#374151]">
          <div className="p-4 border-b border-[#374151]">
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-yellow-400" />
              <h4 className="font-semibold">Recommendations</h4>
            </div>
          </div>
          <div className="p-4">
            <ul className="space-y-2">
              {result.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-gray-300">
                  <span className="text-yellow-400 font-bold">{idx + 1}.</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default ReasoningViewer
