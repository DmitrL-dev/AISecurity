/**
 * SENTINEL Guard — Popup Script.
 * 
 * Handles popup UI state, settings persistence, and stats display.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // ============================================================
  // Load Config
  // ============================================================

  const config = await chrome.storage.sync.get({
    enabled: true,
    autoScan: true,
    sensitivity: 'medium',
    apiKey: '',
  });

  document.getElementById('enableToggle').checked = config.enabled;
  document.getElementById('autoScan').checked = config.autoScan;
  document.getElementById('sensitivity').value = config.sensitivity;
  document.getElementById('apiKey').value = config.apiKey;

  // Update status card based on enabled state
  updateStatusUI(config.enabled);

  // ============================================================
  // Load Stats
  // ============================================================

  const stats = await chrome.storage.local.get({
    totalScans: 0,
    totalBlocked: 0,
    totalWarned: 0,
    totalSafe: 0,
    lastScan: null,
  });

  document.getElementById('totalScans').textContent = formatNumber(stats.totalScans);
  document.getElementById('totalBlocked').textContent = formatNumber(stats.totalBlocked);
  document.getElementById('totalWarned').textContent = formatNumber(stats.totalWarned);
  document.getElementById('totalSafe').textContent = formatNumber(stats.totalSafe);

  // Show last scan result
  if (stats.lastScan) {
    const lastScanEl = document.getElementById('lastScan');
    lastScanEl.style.display = 'block';

    const { verdict, risk_score, timestamp } = stats.lastScan;
    const ago = timeAgo(timestamp);
    const icon = verdict === 'block' ? '🛡️' : verdict === 'warn' ? '⚠️' : '✅';
    const risk = (risk_score * 100).toFixed(0);

    document.getElementById('lastScanResult').innerHTML = 
      `${icon} <strong>${verdict.toUpperCase()}</strong> — Risk: ${risk}% — ${ago}`;
  }

  // ============================================================
  // Event Handlers
  // ============================================================

  // Enable/Disable toggle
  document.getElementById('enableToggle').addEventListener('change', (e) => {
    const enabled = e.target.checked;
    chrome.storage.sync.set({ enabled });
    updateStatusUI(enabled);
  });

  // Auto-scan toggle
  document.getElementById('autoScan').addEventListener('change', (e) => {
    chrome.storage.sync.set({ autoScan: e.target.checked });
  });

  // Sensitivity selector
  document.getElementById('sensitivity').addEventListener('change', (e) => {
    chrome.storage.sync.set({ sensitivity: e.target.value });
  });

  // API Key input (save on blur/change)
  const apiKeyInput = document.getElementById('apiKey');
  apiKeyInput.addEventListener('change', () => {
    chrome.storage.sync.set({ apiKey: apiKeyInput.value.trim() });
  });
  apiKeyInput.addEventListener('blur', () => {
    chrome.storage.sync.set({ apiKey: apiKeyInput.value.trim() });
  });
});

// ============================================================
// UI Helpers
// ============================================================

function updateStatusUI(enabled) {
  const card = document.getElementById('statusCard');
  const icon = document.getElementById('statusIcon');
  const text = document.getElementById('statusText');
  const detail = document.getElementById('statusDetail');

  if (enabled) {
    card.className = 'status-card';
    icon.textContent = '🛡️';
    text.textContent = 'Protection Active';
    detail.textContent = 'Monitoring your AI conversations';
  } else {
    card.className = 'status-card status-disabled';
    icon.textContent = '⏸️';
    text.textContent = 'Protection Paused';
    detail.textContent = 'Your AI conversations are not being monitored';
  }
}

function formatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toString();
}

function timeAgo(timestamp) {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
