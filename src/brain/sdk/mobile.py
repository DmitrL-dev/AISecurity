"""
Mobile Bindings — SENTINEL SDK for iOS/Android/React Native

Provides platform-specific bindings for mobile apps.

Features:
- iOS Swift wrapper
- Android Kotlin wrapper
- React Native bridge
- Flutter plugin (future)

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger("SENTINEL.Mobile")


# ============================================================================
# Platform Detection
# ============================================================================


class Platform(Enum):
    """Mobile platforms."""

    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"
    WEB = "web"
    UNKNOWN = "unknown"


def detect_platform() -> Platform:
    """Detect current platform (would use native detection in production)."""
    # In production, this would check native environment
    return Platform.UNKNOWN


# ============================================================================
# Bridge Protocol
# ============================================================================


@dataclass
class BridgeMessage:
    """Message for native bridge communication."""

    id: str
    method: str
    params: Dict[str, Any]
    platform: Platform


@dataclass
class BridgeResponse:
    """Response from bridge."""

    id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# iOS Bridge
# ============================================================================


class IOSBridge:
    """
    Bridge for iOS Native (Swift/Objective-C).

    Uses JSON serialization for communication with native code.

    Swift usage:
        let sentinel = SentinelSDK(apiKey: "sk_sentinel_xxx")
        sentinel.analyze(prompt: "Hello") { result in
            if result.blocked {
                print("Blocked!")
            }
        }
    """

    @staticmethod
    def generate_swift_interface() -> str:
        """Generate Swift interface code."""
        return '''
import Foundation

public class SentinelSDK {
    private let apiKey: String
    private let baseUrl: String

    public init(apiKey: String, baseUrl: String = "https://api.sentinel.security") {
        self.apiKey = apiKey
        self.baseUrl = baseUrl
    }

    public struct AnalysisResult {
        public let isSafe: Bool
        public let riskScore: Double
        public let riskLevel: String
        public let threats: [String]
        public let blocked: Bool
        public let latencyMs: Double
    }

    public func analyze(
        prompt: String,
        completion: @escaping (Result<AnalysisResult, Error>) -> Void
    ) {
        let url = URL(string: "\\(baseUrl)/v1/analyze")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \\(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["prompt": prompt]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                completion(.failure(NSError(domain: "SentinelSDK", code: -1)))
                return
            }

            let result = AnalysisResult(
                isSafe: json["is_safe"] as? Bool ?? true,
                riskScore: json["risk_score"] as? Double ?? 0,
                riskLevel: json["risk_level"] as? String ?? "safe",
                threats: json["threats"] as? [String] ?? [],
                blocked: json["blocked"] as? Bool ?? false,
                latencyMs: json["latency_ms"] as? Double ?? 0
            )
            completion(.success(result))
        }.resume()
    }

    public func isSafe(prompt: String) async throws -> Bool {
        return try await withCheckedThrowingContinuation { continuation in
            analyze(prompt: prompt) { result in
                switch result {
                case .success(let analysis):
                    continuation.resume(returning: analysis.isSafe)
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}
'''


# ============================================================================
# Android Bridge
# ============================================================================


class AndroidBridge:
    """
    Bridge for Android (Kotlin/Java).

    Kotlin usage:
        val sentinel = SentinelSDK("sk_sentinel_xxx")
        val result = sentinel.analyze("Hello")
        if (result.blocked) {
            Log.w("SENTINEL", "Blocked!")
        }
    """

    @staticmethod
    def generate_kotlin_interface() -> str:
        """Generate Kotlin interface code."""
        return '''
package security.sentinel.sdk

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import org.json.JSONObject

data class AnalysisResult(
    val isSafe: Boolean,
    val riskScore: Double,
    val riskLevel: String,
    val threats: List<String>,
    val blocked: Boolean,
    val latencyMs: Double
)

class SentinelSDK(
    private val apiKey: String,
    private val baseUrl: String = "https://api.sentinel.security"
) {
    private val client = OkHttpClient()
    private val json = "application/json".toMediaType()

    suspend fun analyze(prompt: String): AnalysisResult = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("prompt", prompt)
        }.toString().toRequestBody(json)

        val request = Request.Builder()
            .url("$baseUrl/v1/analyze")
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        val response = client.newCall(request).execute()
        val jsonResponse = JSONObject(response.body?.string() ?: "{}")

        val threats = mutableListOf<String>()
        val threatsArray = jsonResponse.optJSONArray("threats")
        for (i in 0 until (threatsArray?.length() ?: 0)) {
            threats.add(threatsArray?.getString(i) ?: "")
        }

        AnalysisResult(
            isSafe = jsonResponse.optBoolean("is_safe", true),
            riskScore = jsonResponse.optDouble("risk_score", 0.0),
            riskLevel = jsonResponse.optString("risk_level", "safe"),
            threats = threats,
            blocked = jsonResponse.optBoolean("blocked", false),
            latencyMs = jsonResponse.optDouble("latency_ms", 0.0)
        )
    }

    fun isSafe(prompt: String): Boolean {
        return kotlinx.coroutines.runBlocking {
            analyze(prompt).isSafe
        }
    }
}
'''


# ============================================================================
# React Native Bridge
# ============================================================================


class ReactNativeBridge:
    """
    Bridge for React Native.

    JS usage:
        import { SentinelSDK } from 'sentinel-security';

        const sentinel = new SentinelSDK('sk_sentinel_xxx');
        const result = await sentinel.analyze('Hello');

        if (result.blocked) {
            Alert.alert('Blocked!');
        }
    """

    @staticmethod
    def generate_typescript_module() -> str:
        """Generate TypeScript module code."""
        return '''
// sentinel-security.ts

export interface AnalysisResult {
  isSafe: boolean;
  riskScore: number;
  riskLevel: 'safe' | 'low' | 'medium' | 'high' | 'critical';
  threats: string[];
  blocked: boolean;
  latencyMs: number;
  analysisId: string;
}

export interface SDKConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  offlineMode?: boolean;
}

export class SentinelSDK {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  private offlineMode: boolean;

  constructor(config: SDKConfig | string) {
    if (typeof config === 'string') {
      this.apiKey = config;
      this.baseUrl = 'https://api.sentinel.security';
      this.timeout = 30000;
      this.offlineMode = false;
    } else {
      this.apiKey = config.apiKey;
      this.baseUrl = config.baseUrl || 'https://api.sentinel.security';
      this.timeout = config.timeout || 30000;
      this.offlineMode = config.offlineMode || false;
    }
  }

  async analyze(prompt: string, context?: Record<string, any>): Promise<AnalysisResult> {
    if (this.offlineMode) {
      return this.analyzeOffline(prompt);
    }

    const response = await fetch(`${this.baseUrl}/v1/analyze`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt, context }),
    });

    if (!response.ok) {
      throw new Error(`SENTINEL API error: ${response.status}`);
    }

    const data = await response.json();

    return {
      isSafe: data.is_safe,
      riskScore: data.risk_score,
      riskLevel: data.risk_level,
      threats: data.threats || [],
      blocked: data.blocked,
      latencyMs: data.latency_ms,
      analysisId: data.analysis_id,
    };
  }

  async isSafe(prompt: string): Promise<boolean> {
    const result = await this.analyze(prompt);
    return result.isSafe;
  }

  private analyzeOffline(prompt: string): AnalysisResult {
    const lower = prompt.toLowerCase();
    const patterns = [
      { pattern: 'ignore previous', score: 80 },
      { pattern: 'ignore instructions', score: 80 },
      { pattern: 'pretend you are', score: 60 },
      { pattern: 'system prompt', score: 70 },
    ];

    let maxScore = 0;
    const threats: string[] = [];

    for (const { pattern, score } of patterns) {
      if (lower.includes(pattern)) {
        maxScore = Math.max(maxScore, score);
        threats.push(pattern);
      }
    }

    return {
      isSafe: maxScore < 50,
      riskScore: maxScore,
      riskLevel: maxScore < 25 ? 'safe' : maxScore < 50 ? 'low' : maxScore < 70 ? 'medium' : 'high',
      threats,
      blocked: maxScore >= 70,
      latencyMs: 0.1,
      analysisId: 'offline',
    };
  }
}

export default SentinelSDK;
'''


# ============================================================================
# Factory
# ============================================================================


def generate_mobile_bindings(platform: Platform) -> str:
    """Generate platform-specific bindings."""
    if platform == Platform.IOS:
        return IOSBridge.generate_swift_interface()
    elif platform == Platform.ANDROID:
        return AndroidBridge.generate_kotlin_interface()
    elif platform == Platform.REACT_NATIVE:
        return ReactNativeBridge.generate_typescript_module()
    else:
        return ReactNativeBridge.generate_typescript_module()  # Default to TS
