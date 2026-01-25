"use strict";
/**
 * RLM Persistence for Kanban Board
 * Stores tasks in RLM Memory Bridge as L1 facts
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PersistentKanbanBoard = exports.KanbanPersistence = void 0;
const KanbanBoard_1 = require("./KanbanBoard");
/**
 * RLM domains for DevKit
 */
const RLM_DOMAIN = 'devkit-kanban';
/**
 * Persistence service for Kanban Board
 * Uses VS Code extension to communicate with RLM MCP
 */
class KanbanPersistence {
    constructor(board, vscodeApi) {
        this.board = board;
        this.vscodeApi = vscodeApi;
    }
    /**
     * Save board to RLM as a single fact
     */
    async saveBoard() {
        const json = this.board.toJSON();
        if (this.vscodeApi) {
            this.vscodeApi.postMessage({
                command: 'rlm_add_fact',
                content: `kanban_board_state: ${json}`,
                level: 1,
                domain: RLM_DOMAIN
            });
        }
        // Note: localStorage is used in webview (media/main.js), not here
    }
    /**
     * Load board from RLM or return empty board
     * Note: localStorage-based loading is handled in webview (media/main.js)
     */
    async loadBoard() {
        // In extension context, we return empty board
        // Actual state is managed by webview using localStorage
        return new KanbanBoard_1.KanbanBoard();
    }
    /**
     * Save individual task change as fact
     */
    async logTaskChange(task, action) {
        const content = `Task ${action}: [${task.status}] ${task.title}`;
        if (this.vscodeApi) {
            this.vscodeApi.postMessage({
                command: 'rlm_add_fact',
                content,
                level: 1,
                domain: `${RLM_DOMAIN}-log`
            });
        }
    }
    /**
     * Get task history from RLM
     */
    async getTaskHistory(limit = 10) {
        // This would query RLM for recent facts
        // For now, return empty array
        return [];
    }
}
exports.KanbanPersistence = KanbanPersistence;
/**
 * Auto-save wrapper for KanbanBoard
 */
class PersistentKanbanBoard {
    constructor(vscodeApi) {
        this.autoSaveTimeout = null;
        this.autoSaveDelay = 1000; // 1 second debounce
        this.board = new KanbanBoard_1.KanbanBoard();
        this.persistence = new KanbanPersistence(this.board, vscodeApi);
    }
    async initialize() {
        this.board = await this.persistence.loadBoard();
    }
    scheduleAutoSave() {
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }
        this.autoSaveTimeout = setTimeout(() => {
            this.persistence.saveBoard();
        }, this.autoSaveDelay);
    }
    addTask(input) {
        const task = this.board.addTask(input);
        this.persistence.logTaskChange(task, 'created');
        this.scheduleAutoSave();
        return task;
    }
    moveTask(id, status) {
        const task = this.board.getTask(id);
        this.board.moveTask(id, status);
        if (task) {
            this.persistence.logTaskChange({ ...task, status }, 'moved');
        }
        this.scheduleAutoSave();
    }
    updateTask(id, updates) {
        this.board.updateTask(id, updates);
        const task = this.board.getTask(id);
        if (task) {
            this.persistence.logTaskChange(task, 'updated');
        }
        this.scheduleAutoSave();
    }
    deleteTask(id) {
        const task = this.board.getTask(id);
        this.board.deleteTask(id);
        if (task) {
            this.persistence.logTaskChange(task, 'deleted');
        }
        this.scheduleAutoSave();
    }
    reorderTask(id, newOrder) {
        this.board.reorderTask(id, newOrder);
        this.scheduleAutoSave();
    }
    // Proxy methods
    getTask(id) { return this.board.getTask(id); }
    getTasks() { return this.board.getTasks(); }
    getTasksByStatus(status) { return this.board.getTasksByStatus(status); }
    toJSON() { return this.board.toJSON(); }
}
exports.PersistentKanbanBoard = PersistentKanbanBoard;
//# sourceMappingURL=KanbanPersistence.js.map