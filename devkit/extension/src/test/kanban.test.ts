/**
 * Kanban Board Tests
 * TDD: Tests first, implementation after
 */

import * as assert from 'assert';
import { KanbanBoard, Task, TaskStatus, TaskPriority } from '../kanban/KanbanBoard';

suite('Kanban Board Test Suite', () => {

    test('Should create empty board', () => {
        const board = new KanbanBoard();
        assert.strictEqual(board.getTasks().length, 0);
    });

    test('Should add task to board', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'Implement feature X',
            description: 'Details here',
            status: TaskStatus.SPEC
        });

        assert.ok(task.id, 'Task should have an ID');
        assert.strictEqual(task.title, 'Implement feature X');
        assert.strictEqual(board.getTasks().length, 1);
    });

    test('Should move task between columns', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'Test task',
            status: TaskStatus.SPEC
        });

        board.moveTask(task.id, TaskStatus.IN_PROGRESS);
        const updated = board.getTask(task.id);

        assert.strictEqual(updated?.status, TaskStatus.IN_PROGRESS);
    });

    test('Should get tasks by column', () => {
        const board = new KanbanBoard();
        
        board.addTask({ title: 'Task 1', status: TaskStatus.SPEC });
        board.addTask({ title: 'Task 2', status: TaskStatus.SPEC });
        board.addTask({ title: 'Task 3', status: TaskStatus.IN_PROGRESS });

        const specTasks = board.getTasksByStatus(TaskStatus.SPEC);
        const progressTasks = board.getTasksByStatus(TaskStatus.IN_PROGRESS);

        assert.strictEqual(specTasks.length, 2);
        assert.strictEqual(progressTasks.length, 1);
    });

    test('Should delete task', () => {
        const board = new KanbanBoard();
        const task = board.addTask({ title: 'To delete', status: TaskStatus.SPEC });

        board.deleteTask(task.id);

        assert.strictEqual(board.getTasks().length, 0);
        assert.strictEqual(board.getTask(task.id), undefined);
    });

    test('Should update task properties', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'Original',
            status: TaskStatus.SPEC,
            priority: TaskPriority.LOW
        });

        board.updateTask(task.id, {
            title: 'Updated',
            priority: TaskPriority.HIGH
        });

        const updated = board.getTask(task.id);
        assert.strictEqual(updated?.title, 'Updated');
        assert.strictEqual(updated?.priority, TaskPriority.HIGH);
    });

    test('Should reorder tasks within column', () => {
        const board = new KanbanBoard();
        
        const task1 = board.addTask({ title: 'First', status: TaskStatus.SPEC });
        const task2 = board.addTask({ title: 'Second', status: TaskStatus.SPEC });
        const task3 = board.addTask({ title: 'Third', status: TaskStatus.SPEC });

        // Move task3 to first position
        board.reorderTask(task3.id, 0);

        const specTasks = board.getTasksByStatus(TaskStatus.SPEC);
        assert.strictEqual(specTasks[0].id, task3.id);
    });

    test('Should serialize and deserialize board', () => {
        const board = new KanbanBoard();
        board.addTask({ title: 'Task 1', status: TaskStatus.SPEC });
        board.addTask({ title: 'Task 2', status: TaskStatus.IN_PROGRESS });

        const json = board.toJSON();
        const restored = KanbanBoard.fromJSON(json);

        assert.strictEqual(restored.getTasks().length, 2);
    });
});

suite('Task Model Test Suite', () => {

    test('Task should have default priority', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'No priority set',
            status: TaskStatus.SPEC
        });

        assert.strictEqual(task.priority, TaskPriority.MEDIUM);
    });

    test('Task should have createdAt timestamp', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'Timestamped',
            status: TaskStatus.SPEC
        });

        assert.ok(task.createdAt instanceof Date);
    });

    test('Task should track subtasks', () => {
        const board = new KanbanBoard();
        const task = board.addTask({
            title: 'Parent task',
            status: TaskStatus.SPEC,
            subtasks: [
                { title: 'Subtask 1', completed: false },
                { title: 'Subtask 2', completed: true }
            ]
        });

        assert.strictEqual(task.subtasks?.length, 2);
        assert.strictEqual(task.getCompletedSubtasks(), 1);
    });
});
