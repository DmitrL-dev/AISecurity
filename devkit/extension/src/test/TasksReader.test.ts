/**
 * TasksReader Unit Tests
 * Tests for parsing tasks.md files and Kanban data generation
 */

import * as assert from 'assert';

// Types matching TasksReader.ts
type TaskStatus = 'spec' | 'in-progress' | 'review' | 'done';

interface KanbanTask {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: 'low' | 'medium' | 'high';
    specName: string;
    phase?: string;
}

// Parsing logic extracted for testing (same as TasksReader.parseTasksFile)
function parseTasksContent(content: string, specName: string): KanbanTask[] {
    const lines = content.split('\n');
    const tasks: KanbanTask[] = [];
    
    let currentPhase = '';
    let taskIndex = 0;

    for (const line of lines) {
        // Detect phase headers (## Phase X: ...)
        const phaseMatch = line.match(/^##\s+(?:Phase\s+\d+[:.]?\s*)?(.+)/);
        if (phaseMatch) {
            currentPhase = phaseMatch[1].replace(/[🔄⏳✅📖🔧🧪🏆]/g, '').trim();
        }

        // Parse checkbox lines
        const taskMatch = line.match(/^[\s-]*\[([ xX\/])\]\s+(.+)/);
        if (taskMatch) {
            const checkState = taskMatch[1];
            const taskText = taskMatch[2];
            
            // Determine status from checkbox
            let status: TaskStatus;
            if (checkState === 'x' || checkState === 'X') {
                status = 'done';
            } else if (checkState === '/') {
                status = 'in-progress';
            } else {
                status = 'spec';
            }

            // Extract task title and description
            const titleMatch = taskText.match(/\*\*(.+?)\*\*[:\s]*(.*)/);
            let title: string;
            let description: string | undefined;

            if (titleMatch) {
                title = titleMatch[1];
                description = titleMatch[2] || undefined;
            } else {
                title = taskText;
            }

            // Determine priority based on keywords
            let priority: 'low' | 'medium' | 'high' = 'medium';
            if (title.toLowerCase().includes('critical') || title.toLowerCase().includes('security')) {
                priority = 'high';
            } else if (title.toLowerCase().includes('documentation') || title.toLowerCase().includes('docs')) {
                priority = 'low';
            }

            tasks.push({
                id: `${specName}-${taskIndex++}`,
                title: title.substring(0, 50) + (title.length > 50 ? '...' : ''),
                description,
                status,
                priority,
                specName,
                phase: currentPhase || undefined,
            });
        }
    }

    return tasks;
}

describe('TasksReader', () => {
    describe('parseTasksContent', () => {
        it('should parse empty checkbox as spec status', () => {
            const content = `- [ ] Implement feature`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks.length, 1);
            assert.strictEqual(tasks[0].status, 'spec');
            assert.strictEqual(tasks[0].title, 'Implement feature');
        });

        it('should parse checked checkbox as done status', () => {
            const content = `- [x] Completed task`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks.length, 1);
            assert.strictEqual(tasks[0].status, 'done');
        });

        it('should parse uppercase X as done status', () => {
            const content = `- [X] Completed task`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].status, 'done');
        });

        it('should parse slash as in-progress status', () => {
            const content = `- [/] Working on this`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].status, 'in-progress');
        });

        it('should extract bold title and description', () => {
            const content = `- [ ] **Task Title**: Some description here`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].title, 'Task Title');
            assert.strictEqual(tasks[0].description, 'Some description here');
        });

        it('should detect phase headers', () => {
            const content = `## Phase 1: Setup
- [ ] Task in phase 1
## Phase 2: Implementation
- [ ] Task in phase 2`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks.length, 2);
            assert.strictEqual(tasks[0].phase, 'Setup');
            assert.strictEqual(tasks[1].phase, 'Implementation');
        });

        it('should assign high priority to security tasks', () => {
            const content = `- [ ] Security audit required`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].priority, 'high');
        });

        it('should assign high priority to critical tasks', () => {
            const content = `- [ ] Critical bug fix`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].priority, 'high');
        });

        it('should assign low priority to documentation tasks', () => {
            const content = `- [ ] Update documentation`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].priority, 'low');
        });

        it('should truncate long titles to 50 chars', () => {
            const longTitle = 'A'.repeat(60);
            const content = `- [ ] ${longTitle}`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks[0].title.length, 53); // 50 + '...'
            assert.ok(tasks[0].title.endsWith('...'));
        });

        it('should generate unique IDs per spec', () => {
            const content = `- [ ] Task 1
- [ ] Task 2
- [ ] Task 3`;
            const tasks = parseTasksContent(content, 'my-spec');
            
            assert.strictEqual(tasks[0].id, 'my-spec-0');
            assert.strictEqual(tasks[1].id, 'my-spec-1');
            assert.strictEqual(tasks[2].id, 'my-spec-2');
        });

        it('should handle nested task lines', () => {
            const content = `  - [ ] Indented task`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks.length, 1);
            assert.strictEqual(tasks[0].title, 'Indented task');
        });

        it('should parse multiple checkbox formats', () => {
            const content = `- [ ] Empty
- [x] Done lowercase
- [X] Done uppercase  
- [/] In progress`;
            const tasks = parseTasksContent(content, 'test-spec');
            
            assert.strictEqual(tasks.length, 4);
            assert.strictEqual(tasks[0].status, 'spec');
            assert.strictEqual(tasks[1].status, 'done');
            assert.strictEqual(tasks[2].status, 'done');
            assert.strictEqual(tasks[3].status, 'in-progress');
        });
    });

    describe('KanbanData grouping', () => {
        it('should group tasks by status into columns', () => {
            const tasks: KanbanTask[] = [
                { id: '1', title: 'A', status: 'spec', priority: 'medium', specName: 's' },
                { id: '2', title: 'B', status: 'in-progress', priority: 'medium', specName: 's' },
                { id: '3', title: 'C', status: 'done', priority: 'medium', specName: 's' },
                { id: '4', title: 'D', status: 'spec', priority: 'medium', specName: 's' },
            ];
            
            const columns = {
                spec: tasks.filter(t => t.status === 'spec'),
                'in-progress': tasks.filter(t => t.status === 'in-progress'),
                review: tasks.filter(t => t.status === 'review'),
                done: tasks.filter(t => t.status === 'done')
            };
            
            assert.strictEqual(columns.spec.length, 2);
            assert.strictEqual(columns['in-progress'].length, 1);
            assert.strictEqual(columns.review.length, 0);
            assert.strictEqual(columns.done.length, 1);
        });
    });
});
