/**
 * SENTINEL DevKit - Webview Main Script
 * Handles UI logic and VS Code IPC
 */

(function () {
  // State management
  const state = {
    currentView: document.getElementById("root")?.dataset.view || "dashboard",
    tdd: { compliance: 87, tests: 142, coverage: 78 },
    workflow: { phase: "tasks", completed: ["requirements", "design"] },
    qa: {
      iteration: 0,
      maxIterations: 3,
      issues: { high: 0, medium: 0, low: 0 },
      fixed: 0,
      total: 0,
      available: false,
    },
    memory: { L0: 0, L1: 0, L2: 0, L3: 0, total: 0, domains: 0, available: false },
    brain: { connected: false, version: null, engines: 0, message: 'Checking...' },
    pipeline: { status: 'idle', currentAgent: null, currentTask: null, progress: 0, tasksCompleted: 0, tasksTotal: 0, startTime: null },
    logs: [],
    kanban: { tasks: [], columns: null },
    showAddTaskModal: false,
    selectedTask: null,
  };

  // Initialize
  function init() {
    // Setup message handler FIRST
    setupMessageHandler();

    // Request all statuses
    requestAllStatuses();

    // Load kanban state
    loadKanbanState();

    // Initial render
    render();
  }

  // Setup VS Code message handler
  function setupMessageHandler() {
    window.addEventListener("message", (event) => {
      const message = event.data;
      switch (message.command) {
        case "debug":
          console.log('DevKit [from extension]:', message.message);
          break;
        case "navigate":
          state.currentView = message.view;
          render();
          break;
        case "updateState":
          Object.assign(state, message.state);
          render();
          break;
        case "sddStatus":
          if (message.data) {
            state.workflow = {
              phase: message.data.phase,
              completed: message.data.completed,
              specs: message.data.specs,
            };
            render();
          }
          break;
        case "tddStatus":
          if (message.data) {
            state.tdd = {
              compliance: message.data.compliance || 0,
              tests: message.data.tests || 0,
              coverage: message.data.coverage || 0,
              hasTestConfig: message.data.hasTestConfig,
            };
            render();
          }
          break;
        case "rlmStatus":
          if (message.data) {
            state.memory = {
              L0: message.data.L0 || 0,
              L1: message.data.L1 || 0,
              L2: message.data.L2 || 0,
              L3: message.data.L3 || 0,
              total: message.data.total || 0,
              domains: message.data.domains || 0,
              available: message.data.available,
            };
            render();
          }
          break;
        case "kanbanTasks":
          if (message.data) {
            state.kanban = {
              columns: message.data.columns,
              specs: message.data.specs,
              totalTasks: message.data.totalTasks,
              tasks: state.kanban.tasks
            };
            render();
          }
          break;
        case "qaStatus":
          if (message.data) {
            state.qa = {
              iteration: message.data.iteration || 0,
              maxIterations: message.data.maxIterations || 3,
              issues: message.data.issues || { high: 0, medium: 0, low: 0 },
              fixed: message.data.fixed || 0,
              total: message.data.total || 0,
              available: message.data.available,
            };
            render();
          }
          break;
        case "brainStatus":
          if (message.data) {
            state.brain = {
              connected: message.data.connected || false,
              version: message.data.version || null,
              engines: message.data.engines || 0,
              message: message.data.message || 'Unknown',
            };
            render();
          }
          break;
        case "pipelineStatus":
          if (message.data) {
            state.pipeline = {
              status: message.data.status || 'idle',
              currentAgent: message.data.currentAgent || null,
              currentTask: message.data.currentTask || null,
              progress: message.data.progress || 0,
              tasksCompleted: message.data.tasksCompleted || 0,
              tasksTotal: message.data.tasksTotal || 0,
              startTime: message.data.startTime || null,
            };
            state.logs = message.data.logs || [];
            render();
          }
          break;
      }
    });
  }

  // Send message to extension
  function sendMessage(command, data = {}) {
    if (window.vscode) {
      window.vscode.postMessage({ command, data });
    }
  }

  // Request all statuses from extension
  function requestAllStatuses() {
    console.log('DevKit: requestAllStatuses called, vscode available:', !!window.vscode);
    if (window.vscode) {
      console.log('DevKit: Sending getSddStatus, getTddStatus, getRlmStatus, getQaStatus, getBrainStatus, getKanbanTasks');
      window.vscode.postMessage({ command: "getSddStatus" });
      window.vscode.postMessage({ command: "getTddStatus" });
      window.vscode.postMessage({ command: "getRlmStatus" });
      window.vscode.postMessage({ command: "getQaStatus" });
      window.vscode.postMessage({ command: "getBrainStatus" });
      window.vscode.postMessage({ command: "getPipelineStatus" });
      window.vscode.postMessage({ command: "getKanbanTasks" });
    }
  }

  // Render based on current view
  function render() {
    const root = document.getElementById("root");
    if (!root) return;

    switch (state.currentView) {
      case "kanban":
        root.innerHTML = renderKanban();
        break;
      case "sidebar":
        root.innerHTML = renderSidebar();
        break;
      default:
        root.innerHTML = renderDashboard();
    }

    attachEventListeners();
  }

  // Dashboard view
  function renderDashboard() {
    return `
            <div class="dashboard">
                <header class="header">
                    <h1>🛡️ SENTINEL DevKit</h1>
                    <span class="badge badge-active">Active</span>
                </header>

                <div class="grid">
                    ${renderTDDCard()}
                    ${renderWorkflowCard()}
                    ${renderQACard()}
                    ${renderMemoryCard()}
                    ${renderSecurityCard()}
                </div>

                <div class="grid autonomous-grid">
                    ${renderTimelineWidget()}
                    ${renderAgentStatusWidget()}
                    ${renderLiveLogWidget()}
                </div>

                <div class="actions">
                    <button class="btn btn-primary" data-action="openKanban">
                        📋 Open Kanban
                    </button>
                    <button class="btn btn-secondary" data-action="runTDDCheck">
                        🔍 TDD Check
                    </button>
                </div>
            </div>
        `;
  }

  // TDD Card
  function renderTDDCard() {
    const { compliance, tests, coverage } = state.tdd;
    const meterColor =
      compliance >= 80 ? "success" : compliance >= 60 ? "warning" : "error";

    return `
            <div class="card">
                <div class="card-header">
                    <h2>TDD Iron Law</h2>
                    <span class="icon">🔴</span>
                </div>
                <div class="card-body">
                    <div class="meter">
                        <div class="meter-fill meter-${meterColor}" style="width: ${compliance}%"></div>
                    </div>
                    <div class="stats">
                        <div class="stat">
                            <span class="stat-value">${compliance}%</span>
                            <span class="stat-label">Compliance</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${tests}</span>
                            <span class="stat-label">Tests</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${coverage}%</span>
                            <span class="stat-label">Coverage</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  // Workflow Card
  function renderWorkflowCard() {
    const phases = ["requirements", "design", "tasks", "implementation"];
    const { phase, completed, specs } = state.workflow;

    // Render specs list if available
    const specsHtml =
      specs && specs.length > 0
        ? `<div class="specs-list">
                ${specs
                  .map(
                    (s) => `
                    <div class="spec-item">
                        <span class="spec-name">${s.name}</span>
                        <span class="spec-phase spec-${s.phase}">${s.phase}</span>
                        ${s.progress ? `<span class="spec-progress">${s.progress}</span>` : ""}
                    </div>
                `,
                  )
                  .join("")}
               </div>`
        : "";

    return `
            <div class="card">
                <div class="card-header">
                    <h2>SDD Workflow</h2>
                    <span class="icon">📋</span>
                </div>
                <div class="card-body">
                    <div class="workflow">
                        ${phases
                          .map((p) => {
                            const status = completed.includes(p)
                              ? "completed"
                              : p === phase
                                ? "active"
                                : "pending";
                            const icon =
                              status === "completed"
                                ? "✅"
                                : status === "active"
                                  ? "🔄"
                                  : "⏳";
                            return `<div class="step step-${status}"><span>${icon}</span><span>${p}</span></div>`;
                          })
                          .join('<div class="connector"></div>')}
                    </div>
                    ${specsHtml}
                </div>
            </div>
        `;
  }

  // QA Card
  function renderQACard() {
    const { iteration, maxIterations, issues, fixed, total, available } = state.qa;
    
    if (!available && total === 0) {
      return `
            <div class="card">
                <div class="card-header">
                    <h2>QA Fix Loop</h2>
                    <span class="icon">🔄</span>
                </div>
                <div class="card-body">
                    <div class="qa-clean">
                        <span class="clean-icon">✅</span>
                        <span>No issues detected</span>
                    </div>
                </div>
            </div>
        `;
    }

    const progressPercent = total > 0 ? Math.round((fixed / total) * 100) : 0;

    return `
            <div class="card">
                <div class="card-header">
                    <h2>QA Fix Loop</h2>
                    <span class="icon">🔄</span>
                </div>
                <div class="card-body">
                    <div class="qa-status">
                        <div class="iteration">
                            <span class="label">Iteration</span>
                            <span class="value">${iteration} / ${maxIterations}</span>
                        </div>
                        <div class="issues">
                            <span class="issue issue-high" title="Errors">${issues.high}</span>
                            <span class="issue issue-medium" title="Warnings">${issues.medium}</span>
                            <span class="issue issue-low" title="Info">${issues.low}</span>
                        </div>
                    </div>
                    <div class="progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progressPercent}%"></div>
                        </div>
                        <span class="progress-label">${fixed} of ${total} fixed</span>
                    </div>
                </div>
            </div>
        `;
  }

  // Memory Card
  function renderMemoryCard() {
    const { L0, L1, L2, L3, total, domains, available } = state.memory;
    
    if (!available) {
      return `
            <div class="card">
                <div class="card-header">
                    <h2>RLM Memory</h2>
                    <span class="icon">🧠</span>
                </div>
                <div class="card-body">
                    <div class="memory-unavailable">
                        <span class="warning-icon">⚠️</span>
                        <span>RLM not initialized</span>
                        <small>Run <code>rlm_start_session</code></small>
                    </div>
                </div>
            </div>
        `;
    }

    return `
            <div class="card">
                <div class="card-header">
                    <h2>RLM Memory</h2>
                    <span class="icon">🧠</span>
                </div>
                <div class="card-body">
                    <div class="memory-levels">
                        <div class="level level-core"><span class="label">L0 Core</span><span class="count">${L0}</span></div>
                        <div class="level level-domain"><span class="label">L1 Domain</span><span class="count">${L1}</span></div>
                        <div class="level level-module"><span class="label">L2 Module</span><span class="count">${L2}</span></div>
                        <div class="level level-code"><span class="label">L3 Code</span><span class="count">${L3}</span></div>
                    </div>
                    <div class="memory-summary">
                        <span class="total">${total} facts</span>
                        <span class="domains">${domains} domains</span>
                    </div>
                </div>
            </div>
        `;
  }

  // Security Card (Brain Status)
  function renderSecurityCard() {
    const { connected, version, engines, message } = state.brain;
    
    const statusClass = connected ? 'brain-connected' : 'brain-offline';
    const statusIcon = connected ? '🛡️' : '⚠️';
    
    return `
            <div class="card security-card ${statusClass}">
                <div class="card-header">
                    <h2>Security Scanner</h2>
                    <span class="icon">${statusIcon}</span>
                </div>
                <div class="card-body">
                    <div class="brain-status">
                        <span class="status-message">${message}</span>
                    </div>
                    ${connected ? `
                        <div class="brain-info">
                            <span class="version">v${version}</span>
                            <span class="engines">${engines} engines</span>
                        </div>
                    ` : `
                        <div class="brain-warning">
                            <p>Запустите SENTINEL Brain для полного сканирования:</p>
                            <code>cd brain && python -m uvicorn main:app --port 8000</code>
                        </div>
                    `}
                </div>
            </div>
        `;
  }

  // Agent Status Widget - Shows which agent is active
  function renderAgentStatusWidget() {
    const agents = [
      { id: 'researcher', name: 'Researcher', icon: '🔍' },
      { id: 'planner', name: 'Planner', icon: '📋' },
      { id: 'critic', name: 'Spec Critic', icon: '🎯' },
      { id: 'tester', name: 'Tester', icon: '🧪' },
      { id: 'coder', name: 'Coder', icon: '💻' },
      { id: 'security', name: 'Security', icon: '🛡️' },
      { id: 'reviewer', name: 'Reviewer', icon: '👁️' },
      { id: 'fixer', name: 'Fixer', icon: '🔧' }
    ];

    const pipeline = state.pipeline || { 
      status: 'idle', 
      currentAgent: null,
      progress: 0,
      tasksCompleted: 0,
      tasksTotal: 0
    };

    return `
      <div class="card agent-status-card">
        <div class="card-header">
          <h2>Agents</h2>
          <span class="badge badge-${pipeline.status}">${pipeline.status}</span>
        </div>
        <div class="card-body">
          <div class="agent-list">
            ${agents.map(agent => {
              const isActive = pipeline.currentAgent === agent.id;
              const statusClass = isActive ? 'running' : 'idle';
              const indicator = isActive ? '▶' : '○';
              return `
                <div class="agent-item ${statusClass}">
                  <span class="agent-indicator">${indicator}</span>
                  <span class="agent-icon">${agent.icon}</span>
                  <span class="agent-name">${agent.name}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
    `;
  }

  // Timeline Widget - Progress and ETA
  function renderTimelineWidget() {
    const pipeline = state.pipeline || {
      status: 'idle',
      currentTask: null,
      progress: 0,
      tasksCompleted: 0,
      tasksTotal: 0,
      startTime: null
    };

    const elapsedMs = pipeline.startTime ? Date.now() - new Date(pipeline.startTime).getTime() : 0;
    const elapsed = formatDuration(elapsedMs);
    const eta = pipeline.progress > 0 
      ? formatDuration((elapsedMs / pipeline.progress) * (100 - pipeline.progress))
      : '--';

    return `
      <div class="card timeline-card">
        <div class="card-header">
          <h2>Timeline</h2>
          <span class="icon">⏱️</span>
        </div>
        <div class="card-body">
          <div class="timeline-progress">
            <div class="progress-bar-container">
              <div class="progress-bar" style="width: ${pipeline.progress}%"></div>
            </div>
            <span class="progress-text">${pipeline.progress}%</span>
          </div>
          <div class="timeline-stats">
            <div class="stat">
              <span class="label">Tasks</span>
              <span class="value">${pipeline.tasksCompleted}/${pipeline.tasksTotal}</span>
            </div>
            <div class="stat">
              <span class="label">Elapsed</span>
              <span class="value">${elapsed}</span>
            </div>
            <div class="stat">
              <span class="label">ETA</span>
              <span class="value">${eta}</span>
            </div>
          </div>
          ${pipeline.currentTask ? `
            <div class="current-task">
              <span class="label">Current:</span>
              <span class="task-name">${pipeline.currentTask}</span>
            </div>
          ` : ''}
          <div class="timeline-controls">
            <button class="btn btn-sm" data-action="pausePipeline">⏸️ Pause</button>
            <button class="btn btn-sm" data-action="stopPipeline">⏹️ Stop</button>
          </div>
        </div>
      </div>
    `;
  }

  // Live Log Widget - Real-time log
  function renderLiveLogWidget() {
    const logs = state.logs || [];
    const recentLogs = logs.slice(-8);

    return `
      <div class="card live-log-card">
        <div class="card-header">
          <h2>Live Log</h2>
          <span class="log-count">${logs.length}</span>
        </div>
        <div class="card-body">
          <div class="log-entries">
            ${recentLogs.length > 0 ? recentLogs.map(log => `
              <div class="log-entry log-${log.level}">
                <span class="log-time">${formatTime(log.timestamp)}</span>
                <span class="log-agent">[${log.agent}]</span>
                <span class="log-message">${log.message}</span>
              </div>
            `).join('') : `
              <div class="log-empty">No logs yet</div>
            `}
          </div>
        </div>
      </div>
    `;
  }

  // Helper: format duration
  function formatDuration(ms) {
    if (!ms || ms < 0) return '--';
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  }

  // Helper: format time
  function formatTime(timestamp) {
    const d = new Date(timestamp);
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
  }


  // Kanban view (full implementation)
  function renderKanban() {
    // Use real tasks from tasks.md if available, otherwise use localStorage tasks
    const hasRealData =
      state.kanban.columns && Object.keys(state.kanban.columns).length > 0;

    let columns;
    if (hasRealData) {
      columns = [
        {
          id: "spec",
          title: "📝 Spec",
          tasks: state.kanban.columns.spec || [],
        },
        {
          id: "in-progress",
          title: "🔨 In Progress",
          tasks: state.kanban.columns["in-progress"] || [],
        },
        {
          id: "review",
          title: "🔍 Review",
          tasks: state.kanban.columns.review || [],
        },
        {
          id: "done",
          title: "✅ Done",
          tasks: state.kanban.columns.done || [],
        },
      ];
    } else {
      // Fallback to localStorage tasks
      const tasks = state.kanban.tasks || [];
      columns = [
        {
          id: "spec",
          title: "📝 Spec",
          tasks: tasks.filter((t) => t.status === "spec"),
        },
        {
          id: "in-progress",
          title: "🔨 In Progress",
          tasks: tasks.filter((t) => t.status === "in_progress"),
        },
        {
          id: "review",
          title: "🔍 Review",
          tasks: tasks.filter((t) => t.status === "review"),
        },
        {
          id: "done",
          title: "✅ Done",
          tasks: tasks.filter((t) => t.status === "done"),
        },
      ];
    }

    const totalTasks =
      state.kanban.totalTasks ||
      columns.reduce((sum, c) => sum + c.tasks.length, 0);

    return `
            <div class="kanban">
                <header class="header">
                    <button class="btn-back" data-action="goBack">← Back</button>
                    <h1>Kanban Board</h1>
                    <span class="task-count-total">${totalTasks} tasks${hasRealData ? " (from tasks.md)" : ""}</span>
                </header>
                <div class="kanban-board">
                    ${columns
                      .map(
                        (col) => `
                        <div class="column" data-column="${col.id}">
                            <div class="column-header">
                                <h3>${col.title}</h3>
                                <span class="task-count">${col.tasks.length}</span>
                            </div>
                            <div class="tasks" data-column="${col.id}" 
                                ondragover="event.preventDefault()" 
                                ondrop="handleDrop(event, '${col.id}')">
                                ${col.tasks.map((task) => renderTaskCard(task)).join("")}
                            </div>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            </div>
            ${!hasRealData && state.showAddTaskModal ? renderAddTaskModal() : ""}
            ${state.selectedTask ? renderTaskDetailModal() : ""}
        `;
  }

  // Task card
  function renderTaskCard(task) {
    const priorityColors = {
      low: "#3b82f6",
      medium: "#f59e0b",
      high: "#ef4444",
      critical: "#dc2626",
    };

    const subtaskProgress = task.subtasks
      ? `${task.subtasks.filter((s) => s.completed).length}/${task.subtasks.length}`
      : "";

    // Store task data for click handler
    const taskDataAttr = encodeURIComponent(JSON.stringify({
      id: task.id,
      title: task.title,
      description: task.description || '',
      phase: task.phase || '',
      spec: task.spec || '',
      filePath: task.filePath || '',
      lineNumber: task.lineNumber || 0
    }));

    return `
            <div class="task-card" 
                draggable="true" 
                data-task-id="${task.id}"
                data-task-info="${taskDataAttr}"
                ondragstart="handleDragStart(event, '${task.id}')"
                ondragend="handleDragEnd(event)">
                <div class="task-priority" style="background: ${priorityColors[task.priority]}"></div>
                <div class="task-content">
                    <span class="task-title">${task.title}</span>
                    ${task.description ? `<span class="task-desc">${task.description}</span>` : ""}
                    ${subtaskProgress ? `<span class="task-subtasks">☑ ${subtaskProgress}</span>` : ""}
                    ${task.phase ? `<span class="task-phase">📁 ${task.phase}</span>` : ""}
                </div>
            </div>
        `;
  }

  // Add task modal
  function renderAddTaskModal() {
    return `
            <div class="modal-overlay" data-action="closeModal">
                <div class="modal" onclick="event.stopPropagation()">
                    <h2>Add New Task</h2>
                    <form id="add-task-form">
                        <div class="form-group">
                            <label>Title</label>
                            <input type="text" name="title" required placeholder="Task title...">
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <textarea name="description" placeholder="Details..."></textarea>
                        </div>
                        <div class="form-group">
                            <label>Priority</label>
                            <select name="priority">
                                <option value="low">Low</option>
                                <option value="medium" selected>Medium</option>
                                <option value="high">High</option>
                                <option value="critical">Critical</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Column</label>
                            <select name="status">
                                <option value="spec">Spec</option>
                                <option value="in_progress">In Progress</option>
                                <option value="review">Review</option>
                                <option value="done">Done</option>
                            </select>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" data-action="closeModal">Cancel</button>
                            <button type="submit" class="btn btn-primary">Add Task</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
  }

  // Task detail modal
  function renderTaskDetailModal() {
    const task = state.selectedTask;
    if (!task) return '';

    return `
            <div class="modal-overlay task-detail-overlay">
                <div class="modal task-detail-modal">
                    <div class="modal-header">
                        <h2>${task.title}</h2>
                        <button class="btn-close" data-action="closeTaskDetail">×</button>
                    </div>
                    <div class="modal-body">
                        ${task.description ? `
                        <div class="detail-row">
                            <span class="detail-label">Description:</span>
                            <span class="detail-value">${task.description}</span>
                        </div>
                        ` : ''}
                        ${task.phase ? `
                        <div class="detail-row">
                            <span class="detail-label">Phase:</span>
                            <span class="detail-value">${task.phase}</span>
                        </div>
                        ` : ''}
                        ${task.spec ? `
                        <div class="detail-row">
                            <span class="detail-label">Specification:</span>
                            <span class="detail-value">${task.spec}</span>
                        </div>
                        ` : ''}
                        ${task.filePath ? `
                        <div class="detail-row">
                            <span class="detail-label">Source:</span>
                            <span class="detail-value file-path">${task.filePath}${task.lineNumber ? `:${task.lineNumber}` : ''}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-actions">
                        ${task.filePath ? `
                        <button class="btn btn-primary" data-action="openFile">
                            📂 Open in Editor
                        </button>
                        ` : ''}
                        <button class="btn btn-secondary" data-action="closeTaskDetail">Close</button>
                    </div>
                </div>
            </div>
        `;
  }

  // Open task detail modal
  window.openTaskDetail = function(element) {
    const evt = window.event;
    if (evt) evt.stopPropagation();
    try {
      const taskInfo = JSON.parse(decodeURIComponent(element.dataset.taskInfo));
      state.selectedTask = taskInfo;
      render();
    } catch (e) {
      console.error('Error opening task detail:', e);
    }
  };

  // Close task detail modal
  window.closeTaskDetail = function() {
    state.selectedTask = null;
    render();
  };

  // Open task file in editor
  window.openTaskFile = function() {
    if (state.selectedTask && state.selectedTask.filePath) {
      sendMessage('openFile', {
        filePath: state.selectedTask.filePath,
        lineNumber: state.selectedTask.lineNumber || 1
      });
      closeTaskDetail();
    }
  };

  // Drag and drop handlers (global)
  window.handleDragStart = function (e, taskId) {
    e.dataTransfer.setData("text/plain", taskId);
    e.target.classList.add("dragging");
  };

  window.handleDragEnd = function (e) {
    e.target.classList.remove("dragging");
  };

  window.handleDrop = function (e, columnId) {
    e.preventDefault();
    const taskId = e.dataTransfer.getData("text/plain");

    // Update task status
    const task = state.kanban.tasks.find((t) => t.id === taskId);
    if (task && task.status !== columnId) {
      task.status = columnId;
      saveKanbanState();
      render();

      // Notify extension
      sendMessage("taskMoved", { taskId, newStatus: columnId });
    }
  };

  // Kanban state management
  function loadKanbanState() {
    // Only load from localStorage for fallback manual tasks
    // Real tasks from tasks.md come via kanbanTasks message
    const saved = localStorage.getItem("devkit-kanban");
    if (saved) {
      const savedData = JSON.parse(saved);
      // Preserve tasks for fallback, but don't overwrite columns from real data
      state.kanban.tasks = savedData.tasks || [];
    } else {
      // Initialize empty - will be filled with real data from tasks.md
      state.kanban.tasks = [];
    }
  }

  function saveKanbanState() {
    localStorage.setItem("devkit-kanban", JSON.stringify(state.kanban));
  }

  function addNewTask(formData) {
    const task = {
      id: Date.now().toString(),
      title: formData.get("title"),
      description: formData.get("description"),
      priority: formData.get("priority"),
      status: formData.get("status"),
    };
    state.kanban.tasks.push(task);
    saveKanbanState();
    state.showAddTaskModal = false;
    render();
    sendMessage("taskCreated", task);
  }

  function deleteTask(taskId) {
    state.kanban.tasks = state.kanban.tasks.filter((t) => t.id !== taskId);
    saveKanbanState();
    render();
    sendMessage("taskDeleted", { taskId });
  }

  // Sidebar view (compact)
  function renderSidebar() {
    return `
            <div class="sidebar">
                <div class="sidebar-section">
                    <h3>TDD: ${state.tdd.compliance}%</h3>
                    <div class="mini-meter">
                        <div class="meter-fill" style="width: ${state.tdd.compliance}%"></div>
                    </div>
                </div>
                <div class="sidebar-section">
                    <h3>Phase: ${state.workflow.phase}</h3>
                </div>
                <div class="sidebar-section">
                    <h3>QA: ${state.qa.iteration}/${state.qa.maxIterations}</h3>
                </div>
                <button class="btn btn-full" data-action="openFullPanel">
                    Open Dashboard
                </button>
            </div>
        `;
  }

  // Handle actions
  function handleAction(action, el) {
    switch (action) {
      case "openKanban":
        state.currentView = "kanban";
        render();
        break;
      case "goBack":
        state.currentView = "dashboard";
        render();
        break;
      case "openFullPanel":
        sendMessage("openFullPanel", { view: "dashboard" });
        break;
      case "runTDDCheck":
        sendMessage("alert", { text: "Running TDD check..." });
        break;
      case "addTask":
        state.showAddTaskModal = true;
        render();
        break;
      case "closeModal":
        state.showAddTaskModal = false;
        render();
        break;
      case "deleteTask":
        const taskId = el?.dataset?.taskId;
        if (taskId) deleteTask(taskId);
        break;
    }
  }

  // Attach event listeners
  function attachEventListeners() {
    document.querySelectorAll("[data-action]").forEach((el) => {
      el.addEventListener("click", (e) => {
        const action = e.currentTarget.dataset.action;
        handleAction(action, e.currentTarget);
      });
    });

    // Form submission
    const form = document.getElementById("add-task-form");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        addNewTask(new FormData(form));
      });
    }

    // Task card click handler
    document.querySelectorAll(".task-card[data-task-info]").forEach((card) => {
      card.addEventListener("click", (e) => {
        // Don't trigger if dragging
        if (e.target.closest('[draggable="true"]') && e.defaultPrevented) return;
        try {
          const taskInfo = JSON.parse(decodeURIComponent(card.dataset.taskInfo));
          state.selectedTask = taskInfo;
          render();
        } catch (err) {
          console.error('Error opening task detail:', err);
        }
      });
    });

    // Close task detail modal on overlay click
    const modalOverlay = document.querySelector(".task-detail-modal")?.closest(".modal-overlay");
    if (modalOverlay) {
      modalOverlay.addEventListener("click", (e) => {
        if (e.target === modalOverlay) {
          state.selectedTask = null;
          render();
        }
      });
    }

    // Open file button
    document.querySelectorAll("[data-action='openFile']").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (state.selectedTask && state.selectedTask.filePath) {
          sendMessage('openFile', {
            filePath: state.selectedTask.filePath,
            lineNumber: state.selectedTask.lineNumber || 1
          });
          state.selectedTask = null;
          render();
        }
      });
    });

    // Close button in modal
    document.querySelectorAll("[data-action='closeTaskDetail']").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedTask = null;
        render();
      });
    });
  }

  // Start
  init();
})();
