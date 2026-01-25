/**
 * SENTINEL DevKit Dashboard - Application Logic
 * Handles theme switching, data updates, and RLM integration
 */

// Theme Management
function toggleTheme() {
  const html = document.documentElement;
  const themeIcon = document.getElementById("theme-icon");

  if (html.dataset.theme === "light") {
    html.dataset.theme = "dark";
    themeIcon.textContent = "🌙";
    localStorage.setItem("devkit-theme", "dark");
  } else {
    html.dataset.theme = "light";
    themeIcon.textContent = "☀️";
    localStorage.setItem("devkit-theme", "light");
  }
}

// Initialize theme from localStorage
function initTheme() {
  const savedTheme = localStorage.getItem("devkit-theme") || "dark";
  document.documentElement.dataset.theme = savedTheme;
  document.getElementById("theme-icon").textContent =
    savedTheme === "dark" ? "🌙" : "☀️";
}

// Mock data for demo (will be replaced with RLM integration)
const mockData = {
  tdd: {
    compliance: 87,
    tests: 142,
    coverage: 78,
  },
  workflow: {
    current: "tasks", // requirements, design, tasks, implementation
    completed: ["requirements", "design"],
  },
  review: {
    stage1: {
      passed: true,
      checks: ["requirements", "edge_cases", "api_contract"],
    },
    stage2: {
      passed: false,
      checks: ["clean_arch"],
      pending: ["type_hints", "docstrings"],
    },
  },
  qa: {
    iteration: 2,
    maxIterations: 3,
    issues: { high: 1, medium: 3, low: 5 },
    fixed: 6,
    total: 9,
  },
  memory: {
    levels: { L0: 12, L1: 47, L2: 156 },
    recent: [
      { time: "5m ago", text: "Review APPROVED: engine-xyz" },
      { time: "12m ago", text: "TDD violation fixed in shield/" },
      { time: "1h ago", text: "Pattern: unicode edge cases" },
    ],
  },
};

// Update TDD Compliance
function updateTDDCompliance(data) {
  const meter = document.getElementById("tdd-meter");
  const percent = document.getElementById("tdd-percent");
  const tests = document.getElementById("tests-count");
  const coverage = document.getElementById("coverage");

  if (meter) meter.style.width = `${data.compliance}%`;
  if (percent) percent.textContent = `${data.compliance}%`;
  if (tests) tests.textContent = data.tests;
  if (coverage) coverage.textContent = `${data.coverage}%`;

  // Update meter color based on compliance
  if (meter) {
    if (data.compliance >= 80) {
      meter.style.background =
        "linear-gradient(135deg, #10b981 0%, #059669 100%)";
    } else if (data.compliance >= 60) {
      meter.style.background =
        "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)";
    } else {
      meter.style.background =
        "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";
    }
  }
}

// Update QA Progress
function updateQAProgress(data) {
  const iteration = document.getElementById("qa-iteration");
  if (iteration) {
    iteration.textContent = `${data.iteration} / ${data.maxIterations}`;
  }
}

// Simulate real-time updates (for demo)
function simulateUpdates() {
  setInterval(() => {
    // Randomly update TDD compliance slightly
    mockData.tdd.compliance = Math.min(
      100,
      Math.max(70, mockData.tdd.compliance + (Math.random() > 0.5 ? 1 : -1)),
    );
    updateTDDCompliance(mockData.tdd);
  }, 5000);
}

// RLM Integration (placeholder for future MCP connection)
async function fetchRLMData() {
  try {
    // In production, this would call the RLM MCP tools
    // const response = await fetch('/api/rlm/devkit-status');
    // return await response.json();

    console.log("RLM Integration: Using mock data");
    return mockData;
  } catch (error) {
    console.error("Error fetching RLM data:", error);
    return mockData;
  }
}

// Add fact to RLM (placeholder)
async function addRLMFact(content, level = 1, domain = "devkit-review") {
  console.log("RLM: Adding fact", { content, level, domain });
  // In production:
  // await mcpClient.call('rlm-toolkit', 'rlm_add_hierarchical_fact', {
  //     content, level, domain
  // });
}

// Initialize dashboard
async function init() {
  console.log("SENTINEL DevKit Dashboard v1.0");

  // Initialize theme
  initTheme();

  // Fetch initial data
  const data = await fetchRLMData();

  // Update all widgets
  updateTDDCompliance(data.tdd);
  updateQAProgress(data.qa);

  // Start real-time simulation (for demo)
  simulateUpdates();

  console.log("Dashboard initialized");
}

// Run on load
document.addEventListener("DOMContentLoaded", init);

// Export for potential module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    toggleTheme,
    updateTDDCompliance,
    updateQAProgress,
    fetchRLMData,
    addRLMFact,
  };
}
