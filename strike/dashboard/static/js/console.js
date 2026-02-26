/**
 * SENTINEL Strike v3.0 — Console JavaScript
 * Extracted from strike_console.py for maintainability
 */

// State
let eventSource = null;
let currentAttackMode = "web"; // Attack mode: web, llm, hybrid
let currentLang = "en"; // Report language: en, ru
let stats = {
  requests: 0,
  blocked: 0,
  bypasses: 0,
  findings: 0,
  fingerprints: 0,
  geoswitch: 0,
};

// ============================================================
// LANGUAGE SWITCHER (US/RU)
// ============================================================
function setLanguage(lang) {
  currentLang = lang;
  
  // Update button styles
  document.querySelectorAll('.lang-btn').forEach(btn => {
    if (btn.dataset.lang === lang) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  
  // Save to localStorage
  localStorage.setItem('strike_language', lang);
  
  log(`🌍 Report language: ${lang === 'ru' ? 'Русский 🇷🇺' : 'English 🇺🇸'}`, 'info');
}

// Load saved language on startup
document.addEventListener('DOMContentLoaded', function() {
  const savedLang = localStorage.getItem('strike_language');
  if (savedLang) {
    setLanguage(savedLang);
  }
});
// Initialize event listeners when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  // Attack type change handler
  const attackTypeSelect = document.getElementById("attack-type");
  if (attackTypeSelect) {
    attackTypeSelect.addEventListener("change", function () {
      const customSection = document.getElementById("custom-payload-section");
      if (customSection) {
        customSection.style.display =
          this.value === "custom" ? "block" : "none";
      }
    });
  }

  // Browser buttons
  document.querySelectorAll(".browser-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document
        .querySelectorAll(".browser-btn")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
    });
  });

  // Country buttons
  document.querySelectorAll(".country-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document
        .querySelectorAll(".country-btn")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
    });
  });

  // Show custom payload section when 'custom' is checked
  document.querySelectorAll('input[name="attack"]').forEach((cb) => {
    cb.addEventListener("change", function () {
      const customSection = document.getElementById("custom-payload-section");
      const customCb = document.querySelector(
        'input[name="attack"][value="custom"]'
      );
      if (customSection && customCb) {
        customSection.style.display = customCb.checked ? "block" : "none";
      }
      saveSettings(); // Auto-save on change
    });
  });

  // Auto-save on input changes
  document.querySelectorAll("input, select, textarea").forEach((el) => {
    el.addEventListener("change", saveSettings);
  });

  // Load settings and show init log
  loadSettings();
  log("🥷 SENTINEL Strike v3.0 ready", "success");
  log("Select attack vectors and press START", "info");
});

// ============================================================
// COMPLETION NOTIFICATION BANNER
// ============================================================

function showCompletionBanner() {
  // Remove existing banner if any
  const existing = document.getElementById("completion-banner");
  if (existing) existing.remove();
  
  // Create banner
  const banner = document.createElement("div");
  banner.id = "completion-banner";
  banner.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: linear-gradient(135deg, #238636 0%, #1a7f37 100%);
      color: white;
      padding: 20px 40px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(35, 134, 54, 0.5);
      z-index: 10000;
      text-align: center;
      animation: slideDown 0.5s ease;
    ">
      <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 10px;">
        ✅ Сканирование завершено!
      </div>
      <div style="font-size: 1rem; opacity: 0.9;">
        📊 Запросов: <strong>${stats.requests}</strong> | 
        🔓 Bypasses: <strong>${stats.bypasses}</strong> | 
        🎯 Findings: <strong>${stats.findings}</strong>
      </div>
      <button onclick="this.parentElement.parentElement.remove()" style="
        margin-top: 15px;
        background: rgba(255,255,255,0.2);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        padding: 8px 20px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9rem;
      ">✓ Понятно</button>
    </div>
    <style>
      @keyframes slideDown {
        from { transform: translateX(-50%) translateY(-100px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
      }
    </style>
  `;
  document.body.appendChild(banner);
  
  // Auto-remove after 10 seconds
  setTimeout(() => {
    if (banner.parentElement) {
      banner.style.transition = "opacity 0.5s";
      banner.style.opacity = "0";
      setTimeout(() => banner.remove(), 500);
    }
  }, 10000);
}

function log(message, type = "info") {
  const consoleEl = document.getElementById("console");
  if (!consoleEl) return;

  const time = new Date().toLocaleTimeString();
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${message}</span>`;
  consoleEl.appendChild(entry);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function updateStats() {
  const elements = {
    "stat-requests": stats.requests,
    "stat-blocked": stats.blocked,
    "stat-bypasses": stats.bypasses,
    "stat-findings": stats.findings,
    "stat-fingerprints": stats.fingerprints,
    "stat-geoswitch": stats.geoswitch,
  };

  for (const [id, value] of Object.entries(elements)) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
}

function addFinding(finding) {
  const list = document.getElementById("findings-list");
  if (!list) return;

  if (list.querySelector("p")) list.innerHTML = "";

  const div = document.createElement("div");
  div.className = `finding ${finding.severity}`;
  div.innerHTML = `
        <div class="finding-title">[${finding.severity.toUpperCase()}] ${
    finding.type
  }</div>
        <div style="color: #8b949e; font-size: 0.85rem; margin-top: 5px;">
            ${finding.description}<br>
            <code style="color: #a371f7;">${finding.payload || ""}</code>
        </div>
    `;
  list.insertBefore(div, list.firstChild);
}

function startAttack() {
  const target = document.getElementById("target").value;
  if (!target) {
    log("❌ Please enter target URL", "error");
    return;
  }

  // Collect selected web attack types
  const webAttackTypes = [];
  document.querySelectorAll('input[name="attack"]:checked').forEach((cb) => {
    webAttackTypes.push(cb.value);
  });

  // Collect selected LLM attack types
  const llmAttackTypes = [];
  document
    .querySelectorAll('input[name="llm_attack"]:checked')
    .forEach((cb) => {
      llmAttackTypes.push(cb.value);
    });

  // Validate based on mode
  if (currentAttackMode === "web" && webAttackTypes.length === 0) {
    log("❌ Please select at least one web attack vector", "error");
    return;
  }
  if (currentAttackMode === "llm" && llmAttackTypes.length === 0) {
    log("❌ Please select at least one LLM attack vector", "error");
    return;
  }
  if (
    currentAttackMode === "hybrid" &&
    webAttackTypes.length === 0 &&
    llmAttackTypes.length === 0
  ) {
    log("❌ Please select at least one attack vector", "error");
    return;
  }

  // Launch LLM attacks via HYDRA if in LLM or hybrid mode
  if (
    (currentAttackMode === "llm" || currentAttackMode === "hybrid") &&
    llmAttackTypes.length > 0
  ) {
    const llmConfig = {
      target: target,
      attack_types: llmAttackTypes,
      mode: "phantom",
      llm_endpoint:
        document.getElementById("llm-endpoint-type")?.value || "gemini",
      model:
        document.getElementById("llm-model")?.value || "gemini-3-pro-flash",
      gemini_api_key: document.getElementById("gemini-api-key")?.value || null,
      openai_api_key: document.getElementById("openai-api-key")?.value || null,
      // Proxy settings for HYDRA
      scraperapi_key: document.getElementById("scraperapi-key")?.value || null,
      country: document.querySelector(".country-btn.active")?.dataset.country || "us",
    };

    log("🤖 Starting LLM/AI attack via HYDRA...", "info");
    log(`📊 Vectors: ${llmAttackTypes.join(", ")}`, "info");

    // Disable start button during HYDRA attack
    const btnStart = document.getElementById("btn-start");
    if (btnStart) btnStart.disabled = true;

    fetch("/api/hydra/attack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(llmConfig),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          log(`❌ HYDRA Error: ${data.error}`, "error");
          if (btnStart) btnStart.disabled = false;
        } else {
          log(`✅ HYDRA Started: ${data.status || "Running"}`, "success");
          
          // Connect to SSE stream for real-time HYDRA logs
          if (!eventSource) {
            eventSource = new EventSource("/api/attack/stream");
            
            eventSource.onmessage = function (event) {
              const eventData = JSON.parse(event.data);
              handleEvent(eventData);
            };

            eventSource.onerror = function () {
              log("🐙 HYDRA stream closed", "info");
              if (btnStart) btnStart.disabled = false;
              if (eventSource) {
                eventSource.close();
                eventSource = null;
              }
            };
          }
        }
      })
      .catch((e) => {
        log(`❌ HYDRA Error: ${e}`, "error");
        if (btnStart) btnStart.disabled = false;
      });
  }

  // Continue with web attack if in web or hybrid mode
  if (
    (currentAttackMode === "web" || currentAttackMode === "hybrid") &&
    webAttackTypes.length > 0
  ) {
    const attackTypes = webAttackTypes;

    // Collect config
    const config = {
      target: target,
      attack_types: attackTypes,
      param: document.getElementById("param")?.value || "id",
      custom_payload: document.getElementById("custom-payload")?.value || "",
      max_payloads: parseInt(
        document.getElementById("max-payloads")?.value || 20
      ),
      bypass_variants: parseInt(
        document.getElementById("bypass-variants")?.value || 3
      ),
      base_delay: parseFloat(
        document.getElementById("base-delay")?.value || 1.0
      ),
      browser:
        document.querySelector(".browser-btn.active")?.dataset.browser ||
        "chrome_win",
      country:
        document.querySelector(".country-btn.active")?.dataset.country ||
        "auto",
      waf_bypass: {
        encoding: document.getElementById("waf-encoding")?.checked || false,
        unicode: document.getElementById("waf-unicode")?.checked || false,
        comments: document.getElementById("waf-comments")?.checked || false,
        case: document.getElementById("waf-case")?.checked || false,
        hex: document.getElementById("waf-hex")?.checked || false,
        char: document.getElementById("waf-char")?.checked || false,
      },
      stealth: {
        timing: document.getElementById("stealth-timing")?.checked || false,
        fingerprint:
          document.getElementById("stealth-fingerprint")?.checked || false,
        geo: document.getElementById("stealth-geo")?.checked || false,
        detect: document.getElementById("stealth-detect")?.checked || false,
      },
      enterprise: {
        enabled: document.getElementById("enterprise-mode")?.checked || false,
        use_smuggling:
          document.getElementById("use-smuggling")?.checked || false,
        aggression: parseInt(document.getElementById("aggression")?.value || 5),
        concurrent_agents: parseInt(
          document.getElementById("concurrent-agents")?.value || 3
        ),
        burp_proxy: document.getElementById("burp-proxy")?.value || null,
        scraperapi_key:
          document.getElementById("scraperapi-key")?.value || null,
      },
      counter_deception: {
        decoy_payloads: document.getElementById("counter-deception")?.checked || false,
        fingerprint_rotation: document.getElementById("fingerprint-rotation")?.checked || true,
        ai_adaptive: document.getElementById("ai-adaptive")?.checked || false,
      },
    };

    // Reset stats
    stats = {
      requests: 0,
      blocked: 0,
      bypasses: 0,
      findings: 0,
      fingerprints: 0,
      geoswitch: 0,
    };
    updateStats();
    const findingsList = document.getElementById("findings-list");
    if (findingsList) {
      findingsList.innerHTML =
        '<p style="color: #8b949e; text-align: center; padding: 20px;">No vulnerabilities found yet</p>';
    }

    log("🚀 Starting attack on " + target, "attack");
    log("Vectors: " + attackTypes.join(", "), "info");
    log(
      "Aggression: " +
        config.enterprise.aggression +
        "/10" +
        (config.enterprise.enabled ? " [ENTERPRISE]" : ""),
      "stealth"
    );
    log(
      "Browser: " + config.browser + ", Country: " + config.country,
      "stealth"
    );
    if (config.counter_deception.decoy_payloads) {
      log("🍯 Counter-Deception: Decoy payloads ACTIVE", "warning");
    }
    if (config.counter_deception.ai_adaptive) {
      log("🤖 AI Adaptive: Real-time honeypot detection ACTIVE", "success");
    }

    const btnStart = document.getElementById("btn-start");
    if (btnStart) btnStart.disabled = true;

    // Start SSE connection
    fetch("/api/attack/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "started") {
          eventSource = new EventSource("/api/attack/stream");

          eventSource.onmessage = function (event) {
            const data = JSON.parse(event.data);
            handleEvent(data);
          };

          eventSource.onerror = function () {
            log("Connection closed", "warning");
            const btnStart = document.getElementById("btn-start");
            if (btnStart) btnStart.disabled = false;
          };
        }
      });
  }
}

function handleEvent(data) {
  switch (data.type) {
    case "log":
      log(data.message, data.level || "info");
      break;
    case "request":
      stats.requests++;
      break;
    case "blocked":
      stats.blocked++;
      log("⛔ Blocked: " + data.reason, "error");
      break;
    case "bypass":
      stats.bypasses++;
      let bypassMsg =
        "🔓 BYPASS [" +
        (data.severity || "MEDIUM") +
        "] " +
        (data.vector || "UNK") +
        " via " +
        data.technique;
      if (data.response_code) {
        bypassMsg += " (HTTP " + data.response_code + ")";
      }
      log(bypassMsg, "bypass");
      if (data.payload) {
        log(
          "   → Payload: " + data.payload.substring(0, 60) + "...",
          "stealth"
        );
      }
      break;
    case "fingerprint":
      stats.fingerprints++;
      const browserEl = document.getElementById("current-browser");
      if (browserEl) browserEl.textContent = data.browser;
      break;
    case "geoswitch":
      stats.geoswitch++;
      const countryEl = document.getElementById("current-country");
      if (countryEl) countryEl.textContent = data.country;
      log("🌍 Geo switch: " + data.country, "stealth");
      break;
    case "waf":
      const wafEl = document.getElementById("current-waf");
      if (wafEl) wafEl.textContent = data.waf;
      log("🛡️ WAF detected: " + data.waf, "warning");
      break;
    case "finding":
      stats.findings++;
      addFinding(data.finding);
      log(
        "🔓 FOUND: " + data.finding.type + " - " + data.finding.severity,
        "success"
      );
      break;
    case "done":
      log("✅ Attack completed", "success");
      const btnStart = document.getElementById("btn-start");
      if (btnStart) btnStart.disabled = false;
      if (eventSource) eventSource.close();
      
      // === COMPLETION NOTIFICATION ===
      // 1. Show completion summary
      log(`📊 Final stats: ${stats.requests} requests, ${stats.bypasses} bypasses, ${stats.findings} findings`, "success");
      
      // 2. Create prominent completion banner
      showCompletionBanner();
      
      // 3. Browser notification (if permitted)
      if (Notification.permission === "granted") {
        new Notification("🎯 SENTINEL Strike", {
          body: `Scan complete! ${stats.bypasses} bypasses, ${stats.findings} findings`,
          icon: "/static/img/favicon.ico"
        });
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission();
      }
      
      // 4. Play completion sound
      try {
        const audio = new Audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1sbHBgaHVxf3Z5gXl4e3t2e31+fH9+gH5/fn+Af4B/gH+Af4B/gH+Af4B/gH+Af4B/gH+Af4B/gH+Af4B/gH+Af4B/gICAgICAgICAgA==");
        audio.volume = 0.3;
        audio.play().catch(() => {});
      } catch (e) {}
      
      // 5. Scroll to show stats
      const statsSection = document.querySelector(".stat-grid") || document.getElementById("stats");
      if (statsSection) {
        statsSection.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      break;
  }
  updateStats();
}

function stopAttack() {
  fetch("/api/attack/stop", { method: "POST" });
  if (eventSource) eventSource.close();
  log("⏹️ Attack stopped", "warning");
  const btnStart = document.getElementById("btn-start");
  if (btnStart) btnStart.disabled = false;
}

function generateReport() {
  log("📄 Generating professional report...", "info");

  fetch("/api/report/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        log(`❌ Report error: ${data.error}`, "error");
        return;
      }

      log(`✅ Report generated: ${data.report_file}`, "success");
      log(`🎯 Target: ${data.target}`, "info");
      log(
        `📊 Critical: ${data.stats.critical}, High: ${data.stats.high}, Vulns: ${data.stats.unique_vulnerabilities}`,
        "info"
      );

      // Open report in new tab
      const filename = data.report_file.split(/[\\/]/).pop();
      window.open(`/api/report/download/${filename}`, "_blank");
    })
    .catch((e) => log(`❌ Report error: ${e}`, "error"));
}

function exportReport() {
  window.open("/api/report", "_blank");
}

function setAttackMode(mode) {
  console.log("setAttackMode called:", mode);
  currentAttackMode = mode;

  // Update UI - remove active from all, add to clicked
  document.querySelectorAll(".mode-tab").forEach((tab) => {
    if (tab.dataset.mode === mode) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  // Show/hide vector sections
  const webVectors = document.getElementById("web-vectors");
  const llmVectors = document.getElementById("llm-vectors");

  if (!webVectors || !llmVectors) {
    console.error("Vector sections not found!");
    return;
  }

  if (mode === "web") {
    webVectors.style.display = "block";
    llmVectors.style.display = "none";
  } else if (mode === "llm") {
    webVectors.style.display = "none";
    llmVectors.style.display = "block";
  } else {
    // hybrid
    webVectors.style.display = "block";
    llmVectors.style.display = "block";
  }

  log(`🎯 Attack mode: ${mode.toUpperCase()}`, "info");
  saveSettings();
}

function selectAllAttacks() {
  if (currentAttackMode === "web" || currentAttackMode === "hybrid") {
    document
      .querySelectorAll('input[name="attack"]')
      .forEach((cb) => (cb.checked = true));
  }
  if (currentAttackMode === "llm" || currentAttackMode === "hybrid") {
    document
      .querySelectorAll('input[name="llm_attack"]')
      .forEach((cb) => (cb.checked = true));
  }
}

function clearAllAttacks() {
  document
    .querySelectorAll('input[name="attack"]')
    .forEach((cb) => (cb.checked = false));
  document
    .querySelectorAll('input[name="llm_attack"]')
    .forEach((cb) => (cb.checked = false));
}

// Section-specific Select/Clear for each checkbox group
function selectSection(name) {
  document.querySelectorAll(`input[name="${name}"]`).forEach((cb) => (cb.checked = true));
  saveSettings();
}

function clearSection(name) {
  document.querySelectorAll(`input[name="${name}"]`).forEach((cb) => (cb.checked = false));
  saveSettings();
}

// ============================================================
// SETTINGS PERSISTENCE (localStorage)
// ============================================================

const STORAGE_KEY = "strike_console_settings";

function saveSettings() {
  const settings = {
    // Target & Mode
    target: document.getElementById("target")?.value || "",
    attackMode: currentAttackMode,
    param: document.getElementById("param")?.value || "",
    maxPayloads: document.getElementById("max-payloads")?.value || "20",

    // Web attack vectors
    webAttacks: Array.from(
      document.querySelectorAll('input[name="attack"]:checked')
    ).map((cb) => cb.value),

    // LLM attack vectors
    llmAttacks: Array.from(
      document.querySelectorAll('input[name="llm_attack"]:checked')
    ).map((cb) => cb.value),
    llmEndpoint:
      document.getElementById("llm-endpoint-type")?.value || "gemini",
    llmModel: document.getElementById("llm-model")?.value || "",

    // WAF Bypass
    wafEncoding: document.getElementById("waf-encoding")?.checked,
    wafUnicode: document.getElementById("waf-unicode")?.checked,
    wafComments: document.getElementById("waf-comments")?.checked,
    wafCase: document.getElementById("waf-case")?.checked,
    wafHex: document.getElementById("waf-hex")?.checked,
    wafChar: document.getElementById("waf-char")?.checked,

    // Stealth
    stealthTiming: document.getElementById("stealth-timing")?.checked,
    stealthFingerprint: document.getElementById("stealth-fingerprint")?.checked,
    stealthGeo: document.getElementById("stealth-geo")?.checked,
    stealthDetect: document.getElementById("stealth-detect")?.checked,

    // Enterprise
    enterpriseMode: document.getElementById("enterprise-mode")?.checked,
    useSmuggling: document.getElementById("use-smuggling")?.checked,
    aggression: document.getElementById("aggression")?.value,
    concurrentAgents: document.getElementById("concurrent-agents")?.value,
    burpProxy: document.getElementById("burp-proxy")?.value,
    scraperApiKey: document.getElementById("scraperapi-key")?.value,
    geminiApiKey: document.getElementById("gemini-api-key")?.value,
    openaiApiKey: document.getElementById("openai-api-key")?.value,

    // Delays
    baseDelay: document.getElementById("base-delay")?.value,
    bypassVariants: document.getElementById("bypass-variants")?.value,

    // Custom payload
    customPayload: document.getElementById("custom-payload")?.value,

    // Timestamp
    savedAt: new Date().toISOString(),
  };

  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

function loadSettings() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return;

  try {
    const settings = JSON.parse(saved);

    // Target & Mode
    if (settings.target) {
      const el = document.getElementById("target");
      if (el) el.value = settings.target;
    }
    if (settings.param) {
      const el = document.getElementById("param");
      if (el) el.value = settings.param;
    }
    if (settings.maxPayloads) {
      const el = document.getElementById("max-payloads");
      if (el) el.value = settings.maxPayloads;
    }

    // Attack mode
    if (settings.attackMode) setAttackMode(settings.attackMode);

    // Web attack vectors
    document
      .querySelectorAll('input[name="attack"]')
      .forEach((cb) => (cb.checked = false));
    if (settings.webAttacks) {
      settings.webAttacks.forEach((v) => {
        const cb = document.querySelector(`input[name="attack"][value="${v}"]`);
        if (cb) cb.checked = true;
      });
    }

    // LLM attack vectors
    document
      .querySelectorAll('input[name="llm_attack"]')
      .forEach((cb) => (cb.checked = false));
    if (settings.llmAttacks) {
      settings.llmAttacks.forEach((v) => {
        const cb = document.querySelector(
          `input[name="llm_attack"][value="${v}"]`
        );
        if (cb) cb.checked = true;
      });
    }
    if (settings.llmEndpoint) {
      const el = document.getElementById("llm-endpoint-type");
      if (el) el.value = settings.llmEndpoint;
    }
    if (settings.llmModel) {
      const el = document.getElementById("llm-model");
      if (el) el.value = settings.llmModel;
    }

    // WAF Bypass
    const wafFields = [
      "waf-encoding",
      "waf-unicode",
      "waf-comments",
      "waf-case",
      "waf-hex",
      "waf-char",
    ];
    const wafSettings = [
      "wafEncoding",
      "wafUnicode",
      "wafComments",
      "wafCase",
      "wafHex",
      "wafChar",
    ];
    wafFields.forEach((field, i) => {
      const el = document.getElementById(field);
      if (el && settings[wafSettings[i]] !== undefined)
        el.checked = settings[wafSettings[i]];
    });

    // Stealth
    const stealthFields = [
      "stealth-timing",
      "stealth-fingerprint",
      "stealth-geo",
      "stealth-detect",
    ];
    const stealthSettings = [
      "stealthTiming",
      "stealthFingerprint",
      "stealthGeo",
      "stealthDetect",
    ];
    stealthFields.forEach((field, i) => {
      const el = document.getElementById(field);
      if (el && settings[stealthSettings[i]] !== undefined)
        el.checked = settings[stealthSettings[i]];
    });

    // Enterprise
    if (settings.enterpriseMode !== undefined) {
      const el = document.getElementById("enterprise-mode");
      if (el) el.checked = settings.enterpriseMode;
    }
    if (settings.useSmuggling !== undefined) {
      const el = document.getElementById("use-smuggling");
      if (el) el.checked = settings.useSmuggling;
    }
    if (settings.aggression) {
      const el = document.getElementById("aggression");
      const display = document.getElementById("aggression-value");
      if (el) el.value = settings.aggression;
      if (display) display.textContent = settings.aggression;
    }
    if (settings.concurrentAgents) {
      const el = document.getElementById("concurrent-agents");
      const display = document.getElementById("agents-value");
      if (el) el.value = settings.concurrentAgents;
      if (display) display.textContent = settings.concurrentAgents;
    }
    if (settings.burpProxy) {
      const el = document.getElementById("burp-proxy");
      if (el) el.value = settings.burpProxy;
    }
    if (settings.scraperApiKey) {
      const el = document.getElementById("scraperapi-key");
      if (el) el.value = settings.scraperApiKey;
    }
    if (settings.geminiApiKey) {
      const el = document.getElementById("gemini-api-key");
      if (el) el.value = settings.geminiApiKey;
    }
    if (settings.openaiApiKey) {
      const el = document.getElementById("openai-api-key");
      if (el) el.value = settings.openaiApiKey;
    }

    // Delays
    if (settings.baseDelay) {
      const el = document.getElementById("base-delay");
      if (el) el.value = settings.baseDelay;
    }
    if (settings.bypassVariants) {
      const el = document.getElementById("bypass-variants");
      if (el) el.value = settings.bypassVariants;
    }

    // Custom payload
    if (settings.customPayload) {
      const el = document.getElementById("custom-payload");
      if (el) el.value = settings.customPayload;
    }

    log(
      `📂 Settings loaded (saved ${new Date(
        settings.savedAt
      ).toLocaleString()})`,
      "info"
    );
  } catch (e) {
    console.error("Failed to load settings:", e);
  }
}

// ============================================================
// DEEP RECONNAISSANCE
// ============================================================

let discoveredEndpoints = [];

function startDeepRecon() {
  const target = document.getElementById("target").value.trim();
  if (!target) {
    log("❌ Please enter a target URL", "error");
    return;
  }

  const scanIpRange = document.getElementById("scan-ip-range").checked;
  const scraperapiKey = document.getElementById("scraperapi-key")?.value || "";
  const webshareProxy = document.getElementById("webshare-proxy")?.value || "";

  log(`🔍 Starting deep recon on ${target}...`, "info");
  if (webshareProxy) {
    log(`🔗 Using Webshare proxy`, "info");
  } else if (scraperapiKey) {
    log(`🔗 Using ScraperAPI proxy`, "info");
  }

  // Show results container
  document.getElementById("recon-results").style.display = "block";
  document.getElementById("recon-endpoints").innerHTML =
    '<div style="color: #8b949e; text-align: center; padding: 10px;">Scanning...</div>';

  fetch("/api/recon/deep", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: target,
      scan_ip_range: scanIpRange,
      scraperapi_key: scraperapiKey,
      webshare_proxy: webshareProxy,
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "started") {
        log("🔍 Deep recon started, listening for results...", "info");
        // Connect to SSE for real-time updates
        const reconSource = new EventSource("/api/attack/stream");
        reconSource.onmessage = function (event) {
          const msg = JSON.parse(event.data);
          if (msg.type === "log") {
            log(msg.message, msg.level || "info");
          } else if (msg.type === "recon_complete") {
            displayReconResults(msg.data);
            reconSource.close();
          } else if (msg.type === "done") {
            reconSource.close();
          }
        };
        reconSource.onerror = function () {
          reconSource.close();
        };
      } else if (data.error) {
        log(`❌ ${data.error}`, "error");
      }
    })
    .catch((err) => {
      log(`❌ Recon error: ${err}`, "error");
    });
}

function displayReconResults(data) {
  discoveredEndpoints = data.all_endpoints || [];
  const container = document.getElementById("recon-endpoints");
  const countEl = document.getElementById("recon-count");

  countEl.textContent = `${discoveredEndpoints.length} found`;

  if (discoveredEndpoints.length === 0) {
    container.innerHTML =
      '<div style="color: #8b949e; text-align: center; padding: 10px;">No endpoints found</div>';
    return;
  }

  // Icon mapping for all types
  const icons = {
    api: "🔌",
    chat: "💬", 
    admin: "🔐",
    auth: "🔑",
    files: "📁",
    webhooks: "🪝",
    internal: "🔧",
    ai_ml: "🤖",
    widget: "🎨",
    sdk: "📦",
    websocket: "🔗",
    subdomain: "🌐",
    path: "📍",
  };

  let html = "";
  discoveredEndpoints.forEach((ep, i) => {
    const confidence = Math.round((ep.confidence || 0.5) * 100);
    const icon = icons[ep.type] || "📍";
    // Truncate URL for display but keep full URL in title/tooltip
    const displayUrl = ep.url.length > 60 
      ? ep.url.substring(0, 57) + "..." 
      : ep.url;
    
    html += `
      <div style="display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #21262d;">
        <input type="checkbox" class="recon-ep-cb" data-index="${i}" checked style="flex-shrink: 0; width: 14px; cursor: pointer;" />
        <span style="flex-shrink: 0; font-size: 1rem;">${icon}</span>
        <a href="${ep.url}" target="_blank" style="flex: 1; color: #58a6ff; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-decoration: none;" title="${ep.url}">
          ${displayUrl}
        </a>
        <span style="background: #238636; color: #fff; font-size: 0.65rem; padding: 2px 6px; border-radius: 10px; flex-shrink: 0;">${confidence}%</span>
      </div>
    `;
  });
  container.innerHTML = html;

  log(`✅ Found ${discoveredEndpoints.length} endpoints`, "finding");
}

function selectAllEndpoints() {
  document.querySelectorAll(".recon-ep-cb").forEach((cb) => {
    cb.checked = true;
  });
}

function clearEndpoints() {
  document.querySelectorAll(".recon-ep-cb").forEach((cb) => {
    cb.checked = false;
  });
}

function getSelectedEndpoints() {
  const selected = [];
  document.querySelectorAll(".recon-ep-cb:checked").forEach((cb) => {
    const idx = parseInt(cb.dataset.index);
    if (discoveredEndpoints[idx]) {
      selected.push(discoveredEndpoints[idx].url);
    }
  });
  return selected;
}

// ============================================================
// LOAD CACHED RECON RESULTS
// ============================================================

function loadCachedRecon() {
  const target = document.getElementById("target").value.trim();
  if (!target) {
    log("❌ Please enter a target URL to load cached results", "error");
    return;
  }

  log(`📂 Loading cached results for ${target}...`, "info");

  fetch("/api/recon/cache", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target: target }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        log(`❌ ${data.error}`, "error");
        return;
      }
      if (data.cached) {
        log(`✅ Loaded ${data.all_endpoints?.length || 0} cached endpoints from ${data._cached_at}`, "success");
        document.getElementById("recon-results").style.display = "block";
        displayReconResults(data);
      } else {
        log("❌ No cached results found for this target", "warning");
      }
    })
    .catch((err) => {
      log(`❌ Cache load error: ${err}`, "error");
    });
}
