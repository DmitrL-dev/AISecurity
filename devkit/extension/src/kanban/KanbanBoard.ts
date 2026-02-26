/**
 * Kanban Board - Data Model
 * Core entities for task management
 */

import { v4 as uuidv4 } from 'uuid';

/**
 * Task status matching Kanban columns
 */
export enum TaskStatus {
    SPEC = 'spec',
    IN_PROGRESS = 'in_progress',
    REVIEW = 'review',
    DONE = 'done'
}

/**
 * Task priority levels
 */
export enum TaskPriority {
    LOW = 'low',
    MEDIUM = 'medium',
    HIGH = 'high',
    CRITICAL = 'critical'
}

/**
 * Subtask for tracking completion
 */
export interface Subtask {
    title: string;
    completed: boolean;
}

/**
 * Task entity
 */
export interface Task {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    createdAt: Date;
    updatedAt: Date;
    subtasks?: Subtask[];
    labels?: string[];
    assignee?: string;
    order: number;

    // Helper method
    getCompletedSubtasks(): number;
}

/**
 * Task creation input
 */
export interface CreateTaskInput {
    title: string;
    description?: string;
    status: TaskStatus;
    priority?: TaskPriority;
    subtasks?: Subtask[];
    labels?: string[];
    assignee?: string;
}

/**
 * Task update input
 */
export interface UpdateTaskInput {
    title?: string;
    description?: string;
    priority?: TaskPriority;
    subtasks?: Subtask[];
    labels?: string[];
    assignee?: string;
}

/**
 * Internal task implementation
 */
class TaskImpl implements Task {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    createdAt: Date;
    updatedAt: Date;
    subtasks?: Subtask[];
    labels?: string[];
    assignee?: string;
    order: number;

    constructor(input: CreateTaskInput, order: number) {
        this.id = uuidv4();
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

    getCompletedSubtasks(): number {
        if (!this.subtasks) return 0;
        return this.subtasks.filter(s => s.completed).length;
    }
}

/**
 * Kanban Board - manages tasks across columns
 */
export class KanbanBoard {
    private tasks: Map<string, TaskImpl> = new Map();
    private orderCounter: number = 0;

    /**
     * Add a new task to the board
     */
    addTask(input: CreateTaskInput): Task {
        const task = new TaskImpl(input, this.orderCounter++);
        this.tasks.set(task.id, task);
        return task;
    }

    /**
     * Get a task by ID
     */
    getTask(id: string): Task | undefined {
        return this.tasks.get(id);
    }

    /**
     * Get all tasks
     */
    getTasks(): Task[] {
        return Array.from(this.tasks.values())
            .sort((a, b) => a.order - b.order);
    }

    /**
     * Get tasks by status (column)
     */
    getTasksByStatus(status: TaskStatus): Task[] {
        return this.getTasks()
            .filter(t => t.status === status)
            .sort((a, b) => a.order - b.order);
    }

    /**
     * Move task to different column
     */
    moveTask(id: string, newStatus: TaskStatus): void {
        const task = this.tasks.get(id);
        if (task) {
            task.status = newStatus;
            task.updatedAt = new Date();
        }
    }

    /**
     * Update task properties
     */
    updateTask(id: string, updates: UpdateTaskInput): void {
        const task = this.tasks.get(id);
        if (task) {
            if (updates.title !== undefined) task.title = updates.title;
            if (updates.description !== undefined) task.description = updates.description;
            if (updates.priority !== undefined) task.priority = updates.priority;
            if (updates.subtasks !== undefined) task.subtasks = updates.subtasks;
            if (updates.labels !== undefined) task.labels = updates.labels;
            if (updates.assignee !== undefined) task.assignee = updates.assignee;
            task.updatedAt = new Date();
        }
    }

    /**
     * Delete a task
     */
    deleteTask(id: string): void {
        this.tasks.delete(id);
    }

    /**
     * Reorder task within its column
     */
    reorderTask(id: string, newOrder: number): void {
        const task = this.tasks.get(id);
        if (!task) return;

        const sameTasks = this.getTasksByStatus(task.status);
        const currentIndex = sameTasks.findIndex(t => t.id === id);
        
        if (currentIndex === -1 || newOrder === currentIndex) return;

        // Remove and reinsert
        sameTasks.splice(currentIndex, 1);
        sameTasks.splice(newOrder, 0, task);

        // Update order values
        sameTasks.forEach((t, index) => {
            const impl = this.tasks.get(t.id);
            if (impl) impl.order = index;
        });
    }

    /**
     * Serialize board to JSON
     */
    toJSON(): string {
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
    static fromJSON(json: string): KanbanBoard {
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
            (task as any).id = t.id;
            task.createdAt = new Date(t.createdAt);
            task.updatedAt = new Date(t.updatedAt);
            
            board.tasks.set(task.id, task);
        }

        board.orderCounter = data.orderCounter;
        return board;
    }
}
