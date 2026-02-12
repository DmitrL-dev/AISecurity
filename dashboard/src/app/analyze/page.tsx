"use client";

import { useState } from "react";

export default function AnalyzePage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));
    setResult({
      verdict: text.toLowerCase().includes("ignore") ? "BLOCK" : "ALLOW",
      risk_score: text.toLowerCase().includes("ignore") ? 85 : 12,
      threats: text.toLowerCase().includes("ignore") 
        ? ["instruction_override", "jailbreak_attempt"] 
        : [],
      latency_ms: 23.4,
    });
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Analyze Text</h1>

      <div className="card mb-6">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to analyze for security threats..."
          className="w-full h-40 bg-[#111] border border-[#2a2a2a] rounded-lg p-4 text-white resize-none focus:outline-none focus:border-emerald-500"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !text}
          className="btn-primary mt-4 disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {result && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Analysis Result</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-400">Verdict:</span>
              <span className={`ml-2 font-bold ${result.verdict === "ALLOW" ? "status-safe" : "status-danger"}`}>
                {result.verdict}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Risk Score:</span>
              <span className="ml-2 font-bold">{result.risk_score}%</span>
            </div>
            <div>
              <span className="text-gray-400">Latency:</span>
              <span className="ml-2">{result.latency_ms}ms</span>
            </div>
            <div>
              <span className="text-gray-400">Threats:</span>
              <span className="ml-2">
                {result.threats.length > 0 ? result.threats.join(", ") : "None"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
