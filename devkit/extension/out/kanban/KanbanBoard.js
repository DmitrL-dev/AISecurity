"use strict";
/**
 * Kanban Board - Data Model
 * Core entities for task management
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.KanbanBoard = exports.TaskPriority = exports.TaskStatus = void 0;
const uuid_1 = require("uuid");
/**
 * Task status matching Kanban columns
 */
var TaskStatus;
(function (TaskStatus) {
    TaskStatus["SPEC"] = "spec";
    TaskStatus["IN_PROGRESS"] = "in_progress";
    TaskStatus["REVIEW"] = "review";
    TaskStatus["DONE"] = "done";
})(TaskStatus || (exports.TaskStatus = TaskStatus = {}));
/**
 * Task priority levels
 */
var TaskPriority;
(function (TaskPriority) {
    TaskPriority["LOW"] = "low";
    TaskPriority["MEDIUM"] = "medium";
    TaskPriority["HIGH"] = "high";
    TaskPriority["CRITICAL"] = "critical";
})(TaskPriority || (exports.TaskPriority = TaskPriority = {}));
/**
 * Internal task implementation
 */
class TaskImpl {
    constructor(input, order) {
        this.id = (0, uuid_1.v4)();
        this.title = input.title;
        this.description = input.description;
        this.status = input.status;
        this.priority = input.priority ?? TaskPriority.MEDIUM;
        this.createdAt = new Date();
        this.updatedAt = new Date();
        this.subtasks = input.subtasks;
        this.labels = input.labels;
        this.assignee = input.assignee;
        this.order = order;
    }
    getCompletedSubtasks() {
        if (!this.subtasks)
            return 0;
        return this.subtasks.filter(s => s.completed).length;
    }
}
/**
 * Kanban Board - manages tasks across columns
 */
class KanbanBoard {
    constructor() {
        this.tasks = new Map();
        this.orderCounter = 0;
    }
    /**
     * Add a new task to the board
     */
    addTask(input) {
        const task = new TaskImpl(input, this.orderCounter++);
        this.tasks.set(task.id, task);
        return task;
    }
    /**
     * Get a task by ID
     */
    getTask(id) {
        return this.tasks.get(id);
    }
    /**
     * Get all tasks
     */
    getTasks() {
        return Array.from(this.tasks.values())
            .sort((a, b) => a.order - b.order);
    }
    /**
     * Get tasks by status (column)
     */
    getTasksByStatus(status) {
        return this.getTasks()
            .filter(t => t.status === status)
            .sort((a, b) => a.order - b.order);
    }
    /**
     * Move task to different column
     */
    moveTask(id, newStatus) {
        const task = this.tasks.get(id);
        if (task) {
            task.status = newStatus;
            task.updatedAt = new Date();
        }
    }
    /**
     * Update task properties
     */
    updateTask(id, updates) {
        const task = this.tasks.get(id);
        if (task) {
            if (updates.title !== undefined)
                task.title = updates.title;
            if (updates.description !== undefined)
                task.description = updates.description;
            if (updates.priority !== undefined)
                task.priority = updates.priority;
            if (updates.subtasks !== undefined)
                task.subtasks = updates.subtasks;
            if (updates.labels !== undefined)
                task.labels = updates.labels;
            if (updates.assignee !== undefined)
                task.assignee = updates.assignee;
            task.updatedAt = new Date();
        }
    }
    /**
     * Delete a task
     */
    deleteTask(id) {
        this.tasks.delete(id);
    }
    /**
     * Reorder task within its column
     */
    reorderTask(id, newOrder) {
        const task = this.tasks.get(id);
        if (!task)
            return;
        const sameTasks = this.getTasksByStatus(task.status);
        const currentIndex = sameTasks.findIndex(t => t.id === id);
        if (currentIndex === -1 || newOrder === currentIndex)
            return;
        // Remove and reinsert
        sameTasks.splice(currentIndex, 1);
        sameTasks.splice(newOrder, 0, task);
        // Update order values
        sameTasks.forEach((t, index) => {
            const impl = this.tasks.get(t.id);
            if (impl)
                impl.order = index;
        });
    }
    /**
     * Serialize board to JSON
     */
    toJSON() {
        const data = {
            tasks: Array.from(this.tasks.values()).map(t => ({
                id: t.id,
                title: t.title,
                description: t.description,
                status: t.status,
                priority: t.priority,
                createdAt: t.createdAt.toISOString(),
                updatedAt: t.updatedAt.toISOString(),
                subtasks: t.subtasks,
                labels: t.labels,
                assignee: t.assignee,
                order: t.order
            })),
            orderCounter: this.orderCounter
        };
        return JSON.stringify(data);
    }
    /**
     * Deserialize board from JSON
     */
    static fromJSON(json) {
        const board = new KanbanBoard();
        const data = JSON.parse(json);
        for (const t of data.tasks) {
            const task = new TaskImpl({
                title: t.title,
                description: t.description,
                status: t.status,
                priority: t.priority,
                subtasks: t.subtasks,
                labels: t.labels,
                assignee: t.assignee
            }, t.order);
            // Restore original values
            task.id = t.id;
            task.createdAt = new Date(t.createdAt);
            task.updatedAt = new Date(t.updatedAt);
            board.tasks.set(task.id, task);
        }
        board.orderCounter = data.orderCounter;
        return board;
    }
}
exports.KanbanBoard = KanbanBoard;
//# sourceMappingURL=KanbanBoard.js.map