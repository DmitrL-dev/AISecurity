"use strict";
/**
 * Kanban Board Tests
 * TDD: Tests first, implementation after
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("assert"));
const KanbanBoard_1 = require("../kanban/KanbanBoard");
suite('Kanban Board Test Suite', () => {
    test('Should create empty board', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        assert.strictEqual(board.getTasks().length, 0);
    });
    test('Should add task to board', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'Implement feature X',
            description: 'Details here',
            status: KanbanBoard_1.TaskStatus.SPEC
        });
        assert.ok(task.id, 'Task should have an ID');
        assert.strictEqual(task.title, 'Implement feature X');
        assert.strictEqual(board.getTasks().length, 1);
    });
    test('Should move task between columns', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'Test task',
            status: KanbanBoard_1.TaskStatus.SPEC
        });
        board.moveTask(task.id, KanbanBoard_1.TaskStatus.IN_PROGRESS);
        const updated = board.getTask(task.id);
        assert.strictEqual(updated?.status, KanbanBoard_1.TaskStatus.IN_PROGRESS);
    });
    test('Should get tasks by column', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        board.addTask({ title: 'Task 1', status: KanbanBoard_1.TaskStatus.SPEC });
        board.addTask({ title: 'Task 2', status: KanbanBoard_1.TaskStatus.SPEC });
        board.addTask({ title: 'Task 3', status: KanbanBoard_1.TaskStatus.IN_PROGRESS });
        const specTasks = board.getTasksByStatus(KanbanBoard_1.TaskStatus.SPEC);
        const progressTasks = board.getTasksByStatus(KanbanBoard_1.TaskStatus.IN_PROGRESS);
        assert.strictEqual(specTasks.length, 2);
        assert.strictEqual(progressTasks.length, 1);
    });
    test('Should delete task', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({ title: 'To delete', status: KanbanBoard_1.TaskStatus.SPEC });
        board.deleteTask(task.id);
        assert.strictEqual(board.getTasks().length, 0);
        assert.strictEqual(board.getTask(task.id), undefined);
    });
    test('Should update task properties', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'Original',
            status: KanbanBoard_1.TaskStatus.SPEC,
            priority: KanbanBoard_1.TaskPriority.LOW
        });
        board.updateTask(task.id, {
            title: 'Updated',
            priority: KanbanBoard_1.TaskPriority.HIGH
        });
        const updated = board.getTask(task.id);
        assert.strictEqual(updated?.title, 'Updated');
        assert.strictEqual(updated?.priority, KanbanBoard_1.TaskPriority.HIGH);
    });
    test('Should reorder tasks within column', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task1 = board.addTask({ title: 'First', status: KanbanBoard_1.TaskStatus.SPEC });
        const task2 = board.addTask({ title: 'Second', status: KanbanBoard_1.TaskStatus.SPEC });
        const task3 = board.addTask({ title: 'Third', status: KanbanBoard_1.TaskStatus.SPEC });
        // Move task3 to first position
        board.reorderTask(task3.id, 0);
        const specTasks = board.getTasksByStatus(KanbanBoard_1.TaskStatus.SPEC);
        assert.strictEqual(specTasks[0].id, task3.id);
    });
    test('Should serialize and deserialize board', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        board.addTask({ title: 'Task 1', status: KanbanBoard_1.TaskStatus.SPEC });
        board.addTask({ title: 'Task 2', status: KanbanBoard_1.TaskStatus.IN_PROGRESS });
        const json = board.toJSON();
        const restored = KanbanBoard_1.KanbanBoard.fromJSON(json);
        assert.strictEqual(restored.getTasks().length, 2);
    });
});
suite('Task Model Test Suite', () => {
    test('Task should have default priority', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'No priority set',
            status: KanbanBoard_1.TaskStatus.SPEC
        });
        assert.strictEqual(task.priority, KanbanBoard_1.TaskPriority.MEDIUM);
    });
    test('Task should have createdAt timestamp', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'Timestamped',
            status: KanbanBoard_1.TaskStatus.SPEC
        });
        assert.ok(task.createdAt instanceof Date);
    });
    test('Task should track subtasks', () => {
        const board = new KanbanBoard_1.KanbanBoard();
        const task = board.addTask({
            title: 'Parent task',
            status: KanbanBoard_1.TaskStatus.SPEC,
            subtasks: [
                { title: 'Subtask 1', completed: false },
                { title: 'Subtask 2', completed: true }
            ]
        });
        assert.strictEqual(task.subtasks?.length, 2);
        assert.strictEqual(task.getCompletedSubtasks(), 1);
    });
});
//# sourceMappingURL=kanban.test.js.map