import { invoke } from "@tauri-apps/api/core";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { t, setLocale, getCurrentLocale, applyTranslations, initLocale, getAvailableLocales } from "./i18n";

// Types
interface TrafficStats {
  total_connections: number;
  blocked_connections: number;
  allowed_connections: number;
  bytes_inspected: number;
  uptime_seconds: number;
}

interface ProcessInfo {
  pid: number;
  name: string;
  path: string | null;
  memory_mb: number;
}

interface EnhancedLogEntry {
  timestamp: string;
  level: string;
  category: string;
  source: string;
  message: string;
  details?: string;
}

// State
let isEnabled = false;
let processes: ProcessInfo[] = [];
let monitoredPids: number[] = [];
let monitoredApps: string[] = []; // Persisted app names from config
let currentLogLevel = "";
let currentLogCategory = "";

// Format bytes
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Navigation
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const sections = document.querySelectorAll(".section");

  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const sectionId = item.getAttribute("data-section");

      navItems.forEach((n) => n.classList.remove("active"));
      item.classList.add("active");

      sections.forEach((s) => s.classList.remove("active"));
      document.getElementById(`section-${sectionId}`)?.classList.add("active");

      // Load processes when navigating to settings
      if (sectionId === "settings") {
        loadProcesses();
      }
    });
  });
}

// Update stats
async function updateStats() {
  try {
    const stats: TrafficStats = await invoke("get_stats");

    document.getElementById("total-count")!.textContent =
      stats.total_connections.toString();
    document.getElementById("blocked-count")!.textContent =
      stats.blocked_connections.toString();
    document.getElementById("allowed-count")!.textContent =
      stats.allowed_connections.toString();

    document.getElementById("stat-total")!.textContent =
      stats.total_connections.toString();
    document.getElementById("stat-blocked")!.textContent =
      stats.blocked_connections.toString();
    document.getElementById("stat-allowed")!.textContent =
      stats.allowed_connections.toString();
    document.getElementById("stat-bytes")!.textContent = formatBytes(
      stats.bytes_inspected
    );
  } catch (e) {
    console.error("Failed to get stats:", e);
  }
}

// Toggle protection
async function toggleProtection() {
  try {
    isEnabled = await invoke("set_intercept_enabled", { enabled: !isEnabled });
    updateProtectionUI();
  } catch (e) {
    console.error("Failed to toggle:", e);
  }
}

// Update UI
function updateProtectionUI() {
  const shield = document.getElementById("status-shield");
  const title = document.getElementById("status-title");
  const protectionStatus = document.getElementById("protection-status");
  const toggleBtn = document.getElementById("toggle-btn") as HTMLButtonElement;

  if (isEnabled) {
    shield?.classList.add("active");
    title!.textContent = t("home.protectionOn");
    protectionStatus!.className = "status-item success";
    protectionStatus!.innerHTML = `<span class="dot"></span><span data-i18n="home.aiProtectionOn">${t("home.aiProtectionOn")}</span>`;
    toggleBtn.textContent = t("home.disableProtection");
    toggleBtn.classList.add("active");
  } else {
    shield?.classList.remove("active");
    title!.textContent = t("home.protectionOff");
    protectionStatus!.className = "status-item warning";
    protectionStatus!.innerHTML = `<span class="dot"></span><span data-i18n="home.aiProtectionOff">${t("home.aiProtectionOff")}</span>`;
    toggleBtn.textContent = t("home.enableProtection");
    toggleBtn.classList.remove("active");
  }
}

// Load processes
async function loadProcesses() {
  try {
    processes = await invoke("get_processes");
    monitoredPids = await invoke("get_monitored_processes");
    monitoredApps = await invoke("get_monitored_apps"); // Load persisted apps
    renderProcesses();
    renderMonitoredProcesses();
  } catch (e) {
    console.error("Failed to load processes:", e);
  }
}

// Render process list
function renderProcesses(filter: string = "") {
  const list = document.getElementById("process-list");
  if (!list) return;

  // Filter out already monitored processes and apply search
  let available = processes.filter((p) => !monitoredPids.includes(p.pid));
  if (filter) {
    const lowerFilter = filter.toLowerCase();
    available = available.filter((p) =>
      p.name.toLowerCase().includes(lowerFilter)
    );
  }

  if (available.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <span class="empty-icon">🔍</span>
      <p>${t("settings.noProcesses")}</p>
    </div>`;
    return;
  }

  list.innerHTML = available
    .slice(0, 20)
    .map(
      (p) => `
    <div class="process-row" data-pid="${p.pid}">
      <span class="process-icon">📦</span>
      <div class="process-info">
        <div class="process-name">${p.name}</div>
        <div class="process-meta">PID: ${p.pid} • ${p.memory_mb} MB</div>
      </div>
      <button class="btn-add-process" onclick="addProcess(${p.pid}, '${p.name}')">${t("settings.addBtn")}</button>
    </div>
  `
    )
    .join("");
}

// Render monitored processes
function renderMonitoredProcesses() {
  const container = document.getElementById("monitored-processes");
  const countEl = document.getElementById("monitored-count");
  if (!container) return;

  // Show count of persisted apps (not just running PIDs)
  const totalCount = monitoredApps.length || monitoredPids.length;
  if (countEl) countEl.textContent = totalCount.toString();

  if (totalCount === 0) {
    container.innerHTML = `<div class="empty-state">
      <span class="empty-icon">📭</span>
      <p>Добавьте приложения для мониторинга</p>
    </div>`;
    return;
  }

  // Build list from persisted app names
  let html = '';
  
  // Show persisted apps from config
  for (const appName of monitoredApps) {
    // Find running process with this name
    const runningProcess = processes.find(p => 
      p.name.toLowerCase().replace('.exe', '') === appName.toLowerCase()
    );
    
    if (runningProcess) {
      // Process is running
      html += `
        <div class="process-row" data-pid="${runningProcess.pid}">
          <span class="process-icon">🎯</span>
          <div class="process-info">
            <div class="process-name">${runningProcess.name}</div>
            <div class="process-meta">PID: ${runningProcess.pid} • ${t("settings.tracking")}</div>
          </div>
          <button class="btn-remove-process" onclick="removeAppByName('${appName}')">${t("settings.removeBtn")}</button>
        </div>`;
    } else {
      // Process not running - show waiting state
      html += `
        <div class="process-row waiting">
          <span class="process-icon">⏳</span>
          <div class="process-info">
            <div class="process-name">${appName}.exe</div>
            <div class="process-meta">${t("settings.waitingLaunch")}</div>
          </div>
          <button class="btn-remove-process" onclick="removeAppByName('${appName}')">${t("settings.removeBtn")}</button>
        </div>`;
    }
  }
  
  container.innerHTML = html;
}

// Add process to monitoring
async function addProcess(pid: number, _name: string) {
  try {
    await invoke("add_monitored_process", { pid });
    monitoredPids.push(pid);
    renderProcesses();
    renderMonitoredProcesses();
  } catch (e) {
    console.error("Failed to add process:", e);
  }
}

// Remove process from monitoring
async function removeProcess(pid: number) {
  try {
    await invoke("remove_monitored_process", { pid });
    monitoredPids = monitoredPids.filter((p) => p !== pid);
    renderProcesses();
    renderMonitoredProcesses();
  } catch (e) {
    console.error("Failed to remove process:", e);
  }
}

// Remove app by name (from config)
async function removeAppByName(name: string) {
  try {
    await invoke("remove_monitored_app", { name });
    monitoredApps = monitoredApps.filter((a) => a.toLowerCase() !== name.toLowerCase());
    renderProcesses();
    renderMonitoredProcesses();
  } catch (e) {
    console.error("Failed to remove app:", e);
  }
}

// Make functions global for onclick handlers
(window as any).addProcess = addProcess;
(window as any).removeProcess = removeProcess;
(window as any).removeAppByName = removeAppByName;

// Mode selector
function setupModeSelector() {
  const modeOptions = document.querySelectorAll('input[name="mode"]');
  modeOptions.forEach((option) => {
    option.addEventListener("change", async (e) => {
      const value = (e.target as HTMLInputElement).value;
      const isBlock = value === "block";
      try {
        await invoke("set_block_mode", { block: isBlock });
      } catch (e) {
        console.error("Failed to set mode:", e);
      }
    });
  });
}

// Log entry interface
interface LogEntry {
  timestamp: string;
  endpoint: string;
  app_name: string;
  status: string;
  bytes: number;
}

// Demo log interval
let demoLogInterval: ReturnType<typeof setInterval> | null = null;

// Render logs
async function renderLogs() {
  try {
    const logs: LogEntry[] = await invoke("get_logs");
    const container = document.getElementById("logs-container");
    const countEl = document.getElementById("log-count");

    if (countEl) countEl.textContent = logs.length.toString();

    if (!container) return;

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="log-empty">
          <span class="log-empty-icon">📋</span>
          <p>Логи пусты. Включите защиту для начала мониторинга.</p>
        </div>`;
      return;
    }

    container.innerHTML = logs
      .map(
        (log) => `
      <div class="log-entry ${log.status}">
        <span class="log-time">${log.timestamp}</span>
        <span class="log-icon">${getStatusIcon(log.status)}</span>
        <div class="log-details">
          <div class="log-endpoint">${log.endpoint}</div>
          <div class="log-app">${log.app_name} • ${formatBytes(log.bytes)}</div>
        </div>
        <span class="log-status ${log.status}">${getStatusText(
          log.status
        )}</span>
      </div>
    `
      )
      .join("");
  } catch (e) {
    console.error("Failed to render logs:", e);
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case "blocked":
      return "🚫";
    case "allowed":
      return "✅";
    case "analyzed":
      return "🔍";
    case "ai":
      return "🤖";
    default:
      return "📋";
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case "blocked":
      return "Заблокировано";
    case "allowed":
      return "Разрешено";
    case "analyzed":
      return "Анализ";
    case "ai":
      return "AI API";
    default:
      return status;
  }
}

// Load enhanced logs with filters
async function loadEnhancedLogs() {
  try {
    const levelFilter = currentLogLevel || null;
    const categoryFilter = currentLogCategory || null;

    const logs: EnhancedLogEntry[] = await invoke("get_enhanced_logs", {
      count: 100,
      level: levelFilter,
      category: categoryFilter,
    });

    const container = document.getElementById("logs-container");
    const countEl = document.getElementById("log-count");

    if (countEl) countEl.textContent = logs.length.toString();
    if (!container) return;

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="log-empty">
          <span class="log-empty-icon">📋</span>
          <p>Логи пусты. Включите защиту для начала мониторинга.</p>
        </div>`;
      return;
    }

    container.innerHTML = logs
      .map(
        (log) => `
      <div class="log-entry level-${log.level}">
        <span class="log-time">${log.timestamp}</span>
        <span class="log-level-badge ${
          log.level
        }">${log.level.toUpperCase()}</span>
        <span class="log-category-badge">${log.category.toUpperCase()}</span>
        <div class="log-details">
          <div class="log-endpoint">[${log.source}] ${log.message}</div>
          ${log.details ? `<div class="log-app">${log.details}</div>` : ""}
        </div>
      </div>
    `
      )
      .join("");
  } catch (e) {
    console.error("Failed to load enhanced logs:", e);
  }
}

// Setup log filter handlers
function setupLogFilters() {
  const levelSelect = document.getElementById(
    "log-level-filter"
  ) as HTMLSelectElement;
  const categorySelect = document.getElementById(
    "log-category-filter"
  ) as HTMLSelectElement;

  levelSelect?.addEventListener("change", (e) => {
    currentLogLevel = (e.target as HTMLSelectElement).value;
    loadEnhancedLogs();
  });

  categorySelect?.addEventListener("change", (e) => {
    currentLogCategory = (e.target as HTMLSelectElement).value;
    loadEnhancedLogs();
  });
}

// Clear logs
async function clearLogs() {
  try {
    await invoke("clear_logs");
    renderLogs();
  } catch (e) {
    console.error("Failed to clear logs:", e);
  }
}

// Start real connection scanning when protection enabled
function startConnectionScanning() {
  if (demoLogInterval) return;
  demoLogInterval = setInterval(async () => {
    if (isEnabled) {
      try {
        await invoke("scan_connections");
      } catch (e) {
        console.error("Failed to scan connections:", e);
      }
    }
  }, 2000); // Scan every 2 seconds
}

// Stop demo logging
function stopDemoLogging() {
  if (demoLogInterval) {
    clearInterval(demoLogInterval);
    demoLogInterval = null;
  }
}

// Setup language selector
function setupLanguageSelector() {
  const selector = document.getElementById("language-selector") as HTMLSelectElement;
  if (!selector) return;
  
  // Populate options
  const locales = getAvailableLocales();
  const currentLang = getCurrentLocale();
  
  selector.innerHTML = locales.map(loc => 
    `<option value="${loc.code}" ${loc.code === currentLang ? 'selected' : ''}>${loc.name}</option>`
  ).join('');
  
  // Handle change
  selector.addEventListener("change", (e) => {
    const newLocale = (e.target as HTMLSelectElement).value as 'ru' | 'en';
    setLocale(newLocale);
    applyTranslations();
    
    // Also update dynamically generated content
    updateProtectionUI();
  });
}

// Initialize
window.addEventListener("DOMContentLoaded", async () => {
  // Initialize i18n
  initLocale();
  applyTranslations();
  setupLanguageSelector();
  
  setupNavigation();
  setupModeSelector();

  // Auto-enable protection if apps are already being monitored
  try {
    monitoredApps = await invoke("get_monitored_apps");
    if (monitoredApps.length > 0) {
      console.log(`Auto-enabling protection: ${monitoredApps.length} apps monitored`);
      isEnabled = await invoke("set_intercept_enabled", { enabled: true });
      updateProtectionUI();
      startConnectionScanning();
    }
  } catch (e) {
    console.error("Failed to check monitored apps:", e);
  }

  // Toggle button
  document.getElementById("toggle-btn")?.addEventListener("click", async () => {
    await toggleProtection();
    if (isEnabled) startConnectionScanning();
    else stopDemoLogging();
  });

  // Refresh processes button
  document
    .getElementById("refresh-processes")
    ?.addEventListener("click", loadProcesses);

  // Process search
  document.getElementById("process-search")?.addEventListener("input", (e) => {
    const query = (e.target as HTMLInputElement).value;
    renderProcesses(query);
  });

  // Clear logs button
  document.getElementById("clear-logs")?.addEventListener("click", clearLogs);

  // Deep Inspection CA handlers
  document.getElementById("init-ca")?.addEventListener("click", async () => {
    try {
      const path = await invoke<string>("init_ca");
      console.log("CA initialized at:", path);
      checkCaStatus();
    } catch (e) {
      console.error("Failed to init CA:", e);
      alert("Ошибка инициализации CA: " + e);
    }
  });

  document
    .getElementById("open-ca-folder")
    ?.addEventListener("click", async () => {
      try {
        const path = await invoke<string>("get_ca_cert_path");
        // Reveal the cert file in explorer (will open folder with file selected)
        await revealItemInDir(path);
      } catch (e) {
        console.error("Failed to open CA folder:", e);
      }
    });

  // Check CA status on settings load
  async function checkCaStatus() {
    const statusEl = document.getElementById("ca-status");
    const toggleEl = document.getElementById("deep-inspection-toggle");
    if (!statusEl) return;

    try {
      const available = await invoke<boolean>("is_deep_inspection_available");
      if (available) {
        statusEl.className = "ca-status ready";
        statusEl.innerHTML = `
          <span class="status-icon">✅</span>
          <span class="status-text">${t("settings.caCreated")}</span>
        `;
        // Show deep inspection toggle
        if (toggleEl) toggleEl.style.display = "flex";

        // Check if already enabled
        const enabled = await invoke<boolean>("is_deep_inspection_enabled");
        const checkbox = document.getElementById(
          "enable-deep-inspection"
        ) as HTMLInputElement;
        if (checkbox) checkbox.checked = enabled;
      } else {
        statusEl.className = "ca-status not-ready";
        statusEl.innerHTML = `
          <span class="status-icon">⚠️</span>
          <span class="status-text">${t("settings.caNotCreated")}</span>
        `;
        if (toggleEl) toggleEl.style.display = "none";
      }
    } catch (e) {
      console.error("CA status check failed:", e);
    }
  }

  // Deep inspection toggle handler
  document
    .getElementById("enable-deep-inspection")
    ?.addEventListener("change", async (e) => {
      const enabled = (e.target as HTMLInputElement).checked;
      try {
        await invoke("set_deep_inspection", { enabled });
        console.log("Deep inspection:", enabled ? "ENABLED" : "DISABLED");
      } catch (err) {
        console.error("Failed to set deep inspection:", err);
      }
    });

  // Initial CA check
  checkCaStatus();

  // CDN Sync handlers
  async function loadCdnStats() {
    try {
      const stats: { core_patterns: number; cdn_patterns: number; jailbreak_total: number; last_sync: string | null } = 
        await invoke("get_pattern_stats");
      
      // Settings page elements
      const coreEl = document.getElementById("jailbreak-pattern-count");
      const cdnEl = document.getElementById("jailbreak-cdn-count");
      const statusEl = document.getElementById("cdn-sync-status");
      
      // Home page elements
      const homeCountEl = document.getElementById("jailbreak-home-count");
      
      if (coreEl) coreEl.textContent = stats.core_patterns.toString();
      if (cdnEl) cdnEl.textContent = stats.cdn_patterns.toString();
      if (homeCountEl) homeCountEl.textContent = stats.jailbreak_total.toString();
      
      if (statusEl) {
        if (stats.last_sync) {
          statusEl.textContent = `${t("settings.cdnSynced")}: ${stats.last_sync}`;
        } else if (stats.cdn_patterns > 0) {
          statusEl.textContent = `✅ ${stats.cdn_patterns} ${t("settings.cdnPatterns")}`;
        } else {
          statusEl.textContent = t("settings.cdnNoPatterns");
        }
      }
    } catch (e) {
      console.error("Failed to load CDN stats:", e);
      const statusEl = document.getElementById("cdn-sync-status");
      if (statusEl) statusEl.textContent = t("settings.cdnError");
    }
  }

  async function syncCdn() {
    const btn = document.getElementById("btn-sync-cdn") as HTMLButtonElement;
    const statusEl = document.getElementById("cdn-sync-status");
    
    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = `⏳ ${t("settings.cdnSyncing")}`;
    
    try {
      const count: number = await invoke("sync_cdn_patterns");
      if (statusEl) statusEl.textContent = `✅ ${count} ${t("settings.cdnPatterns")}`;
      await loadCdnStats();
    } catch (e) {
      console.error("CDN sync failed:", e);
      if (statusEl) statusEl.textContent = `❌ ${t("settings.cdnError")}: ${e}`;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // Load CDN stats on settings view
  loadCdnStats();
  
  // Sync button handlers (Settings and Home)
  document.getElementById("btn-sync-cdn")?.addEventListener("click", syncCdn);
  document.getElementById("btn-sync-cdn-home")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-sync-cdn-home") as HTMLButtonElement;
    const statusEl = document.getElementById("cdn-home-status");
    
    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = `⏳ ${t("settings.cdnSyncing")}`;
    
    try {
      await invoke("sync_cdn_patterns");
      if (statusEl) statusEl.textContent = `✅ ${t("settings.cdnSynced")}`;
      await loadCdnStats();
      setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
    } catch (e) {
      if (statusEl) statusEl.textContent = `❌ ${e}`;
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  // System Proxy handlers
  async function checkProxyStatus() {
    const statusEl = document.getElementById("proxy-status");
    const iconEl = document.getElementById("proxy-status-icon");
    const textEl = document.getElementById("proxy-status-text");
    const checkbox = document.getElementById(
      "enable-system-proxy"
    ) as HTMLInputElement;
    if (!statusEl) return;

    try {
      const [enabled, server]: [boolean, string] = await invoke(
        "get_system_proxy_status"
      );

      if (enabled && server.includes("18443")) {
        if (iconEl) iconEl.textContent = "✅";
        if (textEl) textEl.textContent = `${t("settings.proxyActive")} ${server}`;
        statusEl.className = "ca-status ready";
        if (checkbox) checkbox.checked = true;
      } else if (enabled) {
        if (iconEl) iconEl.textContent = "⚠️";
        if (textEl) textEl.textContent = `${t("protection.otherProxy")} ${server}`;
        statusEl.className = "ca-status not-ready";
        if (checkbox) checkbox.checked = false;
      } else {
        if (iconEl) iconEl.textContent = "⭕";
        if (textEl) textEl.textContent = t("settings.proxyInactive");
        statusEl.className = "ca-status not-ready";
        if (checkbox) checkbox.checked = false;
      }
    } catch (e) {
      console.error("Proxy status check failed:", e);
      if (iconEl) iconEl.textContent = "❌";
      if (textEl) textEl.textContent = t("common.error");
    }
  }

  // Check proxy status on settings load
  checkProxyStatus();

  // System proxy toggle handler
  document
    .getElementById("enable-system-proxy")
    ?.addEventListener("change", async (e) => {
      const enabled = (e.target as HTMLInputElement).checked;
      try {
        if (enabled) {
          await invoke("enable_system_proxy");
          console.log("System proxy ENABLED");
        } else {
          await invoke("disable_system_proxy");
          console.log("System proxy DISABLED");
        }
        // Update status after change
        setTimeout(checkProxyStatus, 500);
      } catch (err) {
        console.error("Failed to toggle system proxy:", err);
        alert("Ошибка: " + err);
        // Revert checkbox
        (e.target as HTMLInputElement).checked = !enabled;
      }
    });

  // Setup log filters
  setupLogFilters();

  // (Launch with protection removed - legacy feature)

  // Get initial state
  try {
    isEnabled = await invoke("is_intercept_enabled");
    updateProtectionUI();
    if (isEnabled) startConnectionScanning();
  } catch (e) {
    console.error("Init error:", e);
  }

  // Update stats and logs periodically
  updateStats();
  loadEnhancedLogs();
  setInterval(updateStats, 1000);
  setInterval(loadEnhancedLogs, 2000); // Enhanced logs every 2s
});
