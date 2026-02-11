/**
 * SENTINEL Guard — Background Service Worker.
 * 
 * Handles Shield API communication, caching, and badge updates.
 * Manifest V3 requires service workers instead of background pages.
 */

const API_BASE = 'https://api.sentinel.dev';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

// In-memory scan cache (cleared when service worker sleeps)
const scanCache = new Map();

// ============================================================
// Shield API
// ============================================================

async function getConfig() {
  const result = await chrome.storage.sync.get({
    apiKey: '',
    apiUrl: API_BASE,
    enabled: true,
    autoScan: true,
    sensitivity: 'medium',  // low, medium, high
  });
  return result;
}

async function scanText(text) {
  const config = await getConfig();
  
  if (!config.enabled) {
    return { verdict: 'allow', risk_score: 0, threats: [], skipped: true };
  }

  // Check cache
  const cacheKey = hashText(text);
  const cached = scanCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return { ...cached.result, cached: true };
  }

  const headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'sentinel-guard-extension/0.1.0',
  };
  if (config.apiKey) {
    headers['X-API-Key'] = config.apiKey;
  }

  try {
    const response = await fetch(`${config.apiUrl}/analyze`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        text,
        zone: 'browser',
      }),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.error || `HTTP ${response.status}`);
    }

    const result = await response.json();

    // Cache result
    scanCache.set(cacheKey, { result, timestamp: Date.now() });

    // Update badge
    updateBadge(result);

    return result;
  } catch (error) {
    console.error('[SENTINEL] Scan error:', error.message);
    return {
      verdict: 'allow',
      risk_score: 0,
      threats: [],
      error: error.message,
    };
  }
}

// ============================================================
// Badge Updates
// ============================================================

function updateBadge(result) {
  const { verdict, threats = [] } = result;

  if (verdict === 'block') {
    chrome.action.setBadgeBackgroundColor({ color: '#EF4444' });
    chrome.action.setBadgeText({ text: '⛔' });
  } else if (verdict === 'warn') {
    chrome.action.setBadgeBackgroundColor({ color: '#F59E0B' });
    chrome.action.setBadgeText({ text: '⚠' });
  } else {
    chrome.action.setBadgeBackgroundColor({ color: '#10B981' });
    chrome.action.setBadgeText({ text: '✓' });
    // Clear badge after 3 seconds for safe scans
    setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
  }
}

// ============================================================
// Stats Tracking
// ============================================================

async function incrementStats(result) {
  const stats = await chrome.storage.local.get({
    totalScans: 0,
    totalBlocked: 0,
    totalWarned: 0,
    totalSafe: 0,
    threatTypes: {},
    lastScan: null,
  });

  stats.totalScans++;
  if (result.verdict === 'block') stats.totalBlocked++;
  else if (result.verdict === 'warn') stats.totalWarned++;
  else stats.totalSafe++;

  // Track threat types
  for (const threat of result.threats || []) {
    const type = threat.threat_type || 'unknown';
    stats.threatTypes[type] = (stats.threatTypes[type] || 0) + 1;
  }

  stats.lastScan = {
    verdict: result.verdict,
    risk_score: result.risk_score,
    timestamp: Date.now(),
  };

  await chrome.storage.local.set(stats);
}

// ============================================================
// Message Handler
// ============================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SCAN_TEXT') {
    scanText(message.text).then(result => {
      incrementStats(result);
      sendResponse(result);
    }).catch(error => {
      sendResponse({ 
        verdict: 'allow', 
        risk_score: 0, 
        error: error.message 
      });
    });
    return true; // async response
  }

  if (message.type === 'GET_STATS') {
    chrome.storage.local.get({
      totalScans: 0,
      totalBlocked: 0,
      totalWarned: 0,
      totalSafe: 0,
      threatTypes: {},
      lastScan: null,
    }).then(sendResponse);
    return true;
  }

  if (message.type === 'GET_CONFIG') {
    getConfig().then(sendResponse);
    return true;
  }
});

// ============================================================
// Install Handler
// ============================================================

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    // Set defaults
    chrome.storage.sync.set({
      enabled: true,
      autoScan: true,
      sensitivity: 'medium',
      apiKey: '',
      apiUrl: API_BASE,
    });
    console.log('[SENTINEL] Extension installed — ready to protect your AI conversations!');
  }
});

// ============================================================
// Utilities
// ============================================================

function hashText(text) {
  // Simple hash for cache keys (not cryptographic)
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const char = text.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return hash.toString(36);
}
