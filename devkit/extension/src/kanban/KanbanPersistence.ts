/**
 * RLM Persistence for Kanban Board
 * Stores tasks in RLM Memory Bridge as L1 facts
 */

import { KanbanBoard, Task, TaskStatus } from './KanbanBoard';

/**
 * RLM domains for DevKit
 */
const RLM_DOMAIN = 'devkit-kanban';

/**
 * Message to send to extension for RLM operations
 */
export interface RLMMessage {
    command: 'rlm_add_fact' | 'rlm_search' | 'rlm_get_domain';
    content?: string;
    level?: number;
    domain?: string;
    query?: string;
}

/**
 * Persistence service for Kanban Board
 * Uses VS Code extension to communicate with RLM MCP
 */
export class KanbanPersistence {
    private board: KanbanBoard;
    private vscodeApi: any;

    constructor(board: KanbanBoard, vscodeApi?: any) {
        this.board = board;
        this.vscodeApi = vscodeApi;
    }

    /**
     * Save board to RLM as a single fact
     */
    async saveBoard(): Promise<void> {
        const json = this.board.toJSON();
        
        if (this.vscodeApi) {
            this.vscodeApi.postMessage({
                command: 'rlm_add_fact',
                content: `kanban_board_state: ${json}`,
                level: 1,
                domain: RLM_DOMAIN
            } as RLMMessage);
        }
        // Note: localStorage is used in webview (media/main.js), not here
    }

    /**
     * Load board from RLM or return empty board
     * Note: localStorage-based loading is handled in webview (media/main.js)
     */
    async loadBoard(): Promise<KanbanBoard> {
        // In extension context, we return empty board
        // Actual state is managed by webview using localStorage
        return new KanbanBoard();
    }

    /**
     * Save individual task change as fact
     */
    async logTaskChange(task: Task, action: 'created' | 'moved' | 'updated' | 'deleted'): Promise<void> {
        const content = `Task ${action}: [${task.status}] ${task.title}`;
        
        if (this.vscodeApi) {
            this.vscodeApi.postMessage({
                command: 'rlm_add_fact',
                content,
                level: 1,
                domain: `${RLM_DOMAIN}-log`
            } as RLMMessage);
        }
    }

    /**
     * Get task history from RLM
     */
    async getTaskHistory(limit: number = 10): Promise<string[]> {
        // This would query RLM for recent facts
        // For now, return empty array
        return [];
    }
}

/**
 * Auto-save wrapper for KanbanBoard
 */
export class PersistentKanbanBoard {
    private board: KanbanBoard;
    private persistence: KanbanPersistence;
    private autoSaveTimeout: NodeJS.Timeout | null = null;
    private autoSaveDelay: number = 1000; // 1 second debounce

    constructor(vscodeApi?: any) {
        this.board = new KanbanBoard();
        this.persistence = new KanbanPersistence(this.board, vscodeApi);
    }

    async initialize(): Promise<void> {
        this.board = await this.persistence.loadBoard();
    }

    private scheduleAutoSave(): void {
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }
        this.autoSaveTimeout = setTimeout(() => {
            this.persistence.saveBoard();
        }, this.autoSaveDelay);
    }

    addTask(input: Parameters<KanbanBoard['addTask']>[0]): Task {
        const task = this.board.addTask(input);
        this.persistence.logTaskChange(task, 'created');
        this.scheduleAutoSave();
        return task;
    }

    moveTask(id: string, status: TaskStatus): void {
        const task = this.board.getTask(id);
        this.board.moveTask(id, status);
        if (task) {
            this.persistence.logTaskChange({ ...task, status }, 'moved');
        }
        this.scheduleAutoSave();
    }

    updateTask(id: string, updates: Parameters<KanbanBoard['updateTask']>[1]): void {
        this.board.updateTask(id, updates);
        const task = this.board.getTask(id);
        if (task) {
            this.persistence.logTaskChange(task, 'updated');
        }
        this.scheduleAutoSave();
    }

    deleteTask(id: string): void {
        const task = this.board.getTask(id);
        this.board.deleteTask(id);
        if (task) {
            this.persistence.logTaskChange(task, 'deleted');
        }
        this.scheduleAutoSave();
    }

    reorderTask(id: string, newOrder: number): void {
        this.board.reorderTask(id, newOrder);
        this.scheduleAutoSave();
    }

    // Proxy methods
    getTask(id: string) { return this.board.getTask(id); }
    getTasks() { return this.board.getTasks(); }
    getTasksByStatus(status: TaskStatus) { return this.board.getTasksByStatus(status); }
    toJSON() { return this.board.toJSON(); }
}
