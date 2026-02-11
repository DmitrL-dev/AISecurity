/**
 * SENTINEL Guard — Content Script.
 * 
 * Injected into ChatGPT, Claude, Gemini, Perplexity pages.
 * Intercepts user prompts before submission and scans them via Shield API.
 */

(function() {
  'use strict';

  const SELECTORS = {
    // ChatGPT
    'chatgpt.com': {
      input: '#prompt-textarea, textarea[data-id="root"]',
      sendButton: 'button[data-testid="send-button"], button[aria-label="Send prompt"]',
      form: 'form',
    },
    'chat.openai.com': {
      input: '#prompt-textarea, textarea[data-id="root"]',
      sendButton: 'button[data-testid="send-button"]',
      form: 'form',
    },
    // Claude
    'claude.ai': {
      input: 'div[contenteditable="true"], textarea',
      sendButton: 'button[aria-label="Send Message"], button[type="submit"]',
      form: 'form',
    },
    // Gemini
    'gemini.google.com': {
      input: 'rich-textarea div[contenteditable="true"], textarea',
      sendButton: 'button[aria-label="Send message"]',
      form: 'form',
    },
    // Perplexity
    'www.perplexity.ai': {
      input: 'textarea',
      sendButton: 'button[aria-label="Submit"]',
      form: 'form',
    },
  };

  const hostname = window.location.hostname;
  const config = SELECTORS[hostname];

  if (!config) {
    console.log('[SENTINEL] No config for', hostname);
    return;
  }

  let isScanning = false;
  let lastScannedText = '';
  let notificationTimeout = null;

  // ============================================================
  // UI: Floating Shield Indicator
  // ============================================================

  function createIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'sentinel-indicator';
    indicator.innerHTML = `
      <div class="sentinel-badge" title="SENTINEL Guard">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <span class="sentinel-status">●</span>
      </div>
    `;
    document.body.appendChild(indicator);
    return indicator;
  }

  function updateIndicator(verdict, riskScore) {
    const indicator = document.getElementById('sentinel-indicator');
    if (!indicator) return;

    const status = indicator.querySelector('.sentinel-status');
    const badge = indicator.querySelector('.sentinel-badge');

    if (verdict === 'block') {
      status.style.color = '#EF4444';
      badge.style.borderColor = '#EF4444';
      badge.title = `SENTINEL: BLOCKED (risk: ${(riskScore * 100).toFixed(0)}%)`;
    } else if (verdict === 'warn') {
      status.style.color = '#F59E0B';
      badge.style.borderColor = '#F59E0B';
      badge.title = `SENTINEL: WARNING (risk: ${(riskScore * 100).toFixed(0)}%)`;
    } else {
      status.style.color = '#10B981';
      badge.style.borderColor = '#10B981';
      badge.title = 'SENTINEL: Safe';
    }
  }

  // ============================================================
  // UI: Notification Toast
  // ============================================================

  function showNotification(result) {
    // Remove existing notification
    const existing = document.getElementById('sentinel-notification');
    if (existing) existing.remove();
    if (notificationTimeout) clearTimeout(notificationTimeout);

    const { verdict, risk_score, threats = [] } = result;

    // Don't show notification for safe prompts
    if (verdict === 'allow') return;

    const notification = document.createElement('div');
    notification.id = 'sentinel-notification';
    notification.className = `sentinel-toast sentinel-toast-${verdict}`;

    const threatList = threats.map(t => t.threat_type).join(', ');
    const icon = verdict === 'block' ? '🛡️' : '⚠️';
    const title = verdict === 'block' ? 'Prompt Blocked' : 'Security Warning';
    const riskPercent = (risk_score * 100).toFixed(0);

    notification.innerHTML = `
      <div class="sentinel-toast-header">
        <span class="sentinel-toast-icon">${icon}</span>
        <span class="sentinel-toast-title">${title}</span>
        <button class="sentinel-toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
      <div class="sentinel-toast-body">
        <div class="sentinel-toast-risk">Risk: ${riskPercent}%</div>
        ${threatList ? `<div class="sentinel-toast-threats">Detected: ${threatList}</div>` : ''}
      </div>
      <div class="sentinel-toast-bar">
        <div class="sentinel-toast-bar-fill" style="width: ${riskPercent}%"></div>
      </div>
    `;

    document.body.appendChild(notification);

    // Auto-dismiss after 8 seconds for warnings, keep for blocks
    if (verdict !== 'block') {
      notificationTimeout = setTimeout(() => notification.remove(), 8000);
    }
  }

  // ============================================================
  // Core: Intercept and Scan
  // ============================================================

  function getPromptText() {
    const el = document.querySelector(config.input);
    if (!el) return '';

    // Handle contenteditable divs (Claude, Gemini)
    if (el.getAttribute('contenteditable') === 'true') {
      return el.innerText || el.textContent || '';
    }
    // Handle textareas
    return el.value || '';
  }

  async function scanPrompt(text) {
    if (!text || text.length < 5) return null;
    if (text === lastScannedText) return null;
    if (isScanning) return null;

    isScanning = true;
    lastScannedText = text;

    try {
      const result = await chrome.runtime.sendMessage({
        type: 'SCAN_TEXT',
        text: text,
      });

      updateIndicator(result.verdict, result.risk_score);
      showNotification(result);

      return result;
    } catch (error) {
      console.error('[SENTINEL] Scan error:', error);
      return null;
    } finally {
      isScanning = false;
    }
  }

  // ============================================================
  // Intercept: Submit Handler
  // ============================================================

  function interceptSubmit() {
    // Listen for Enter key in the input area
    document.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        const text = getPromptText();
        if (text.length >= 5) {
          const result = await scanPrompt(text);
          if (result && result.verdict === 'block') {
            e.preventDefault();
            e.stopPropagation();
            showNotification(result);
            return false;
          }
        }
      }
    }, true); // capture phase to intercept before the app

    // Listen for clicks on send buttons
    document.addEventListener('click', async (e) => {
      const btn = e.target.closest(config.sendButton);
      if (btn) {
        const text = getPromptText();
        if (text.length >= 5) {
          const result = await scanPrompt(text);
          if (result && result.verdict === 'block') {
            e.preventDefault();
            e.stopPropagation();
            showNotification(result);
            return false;
          }
        }
      }
    }, true);
  }

  // ============================================================
  // Auto-Scan: Debounced input monitoring
  // ============================================================

  let autoScanTimer = null;

  function startAutoScan() {
    // Watch for text changes in the input area
    const observer = new MutationObserver(() => {
      clearTimeout(autoScanTimer);
      autoScanTimer = setTimeout(async () => {
        const text = getPromptText();
        if (text.length >= 20) { // Only auto-scan substantial text
          await scanPrompt(text);
        }
      }, 1500); // Debounce 1.5s
    });

    // Observe the input area for changes
    function tryObserve() {
      const inputEl = document.querySelector(config.input);
      if (inputEl) {
        observer.observe(inputEl, {
          childList: true,
          subtree: true,
          characterData: true,
        });
        console.log('[SENTINEL] Watching', hostname, 'input for threats');
        return true;
      }
      return false;
    }

    // Retry until input element appears (SPA loading)
    if (!tryObserve()) {
      let retries = 0;
      const interval = setInterval(() => {
        if (tryObserve() || retries++ > 20) {
          clearInterval(interval);
        }
      }, 1000);
    }
  }

  // ============================================================
  // Init
  // ============================================================

  function init() {
    createIndicator();
    interceptSubmit();
    startAutoScan();
    console.log(`[SENTINEL] Guard active on ${hostname}`);
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
