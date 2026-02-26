/**
 * KiroSpecReader Unit Tests
 * Tests for spec phase detection and task progress parsing
 */

import * as assert from 'assert';

// Types from KiroSpecReader.ts
type SDDPhase = 'requirements' | 'design' | 'tasks' | 'implementation' | 'complete';

interface SpecStatus {
    name: string;
    phase: SDDPhase;
    hasRequirements: boolean;
    hasDesign: boolean;
    hasTasks: boolean;
    taskProgress?: { completed: number; total: number };
}

// Phase detection logic (same as readSpecStatus)
function determinePhase(
    hasRequirements: boolean, 
    hasDesign: boolean, 
    hasTasks: boolean,
    taskProgress?: { completed: number; total: number }
): SDDPhase {
    let phase: SDDPhase = 'requirements';
    
    if (hasRequirements && !hasDesign) {
        phase = 'design';
    } else if (hasDesign && !hasTasks) {
        phase = 'tasks';
    } else if (hasTasks) {
        phase = 'implementation';
    }
    
    // Check if complete
    if (taskProgress && taskProgress.completed === taskProgress.total && taskProgress.total > 0) {
        phase = 'complete';
    }
    
    return phase;
}

// Task progress parsing (same as readTaskProgress)
function parseTaskProgress(content: string): { completed: number; total: number } {
    const totalMatch = content.match(/\[[ xX\/]\]/g);
    const completedMatch = content.match(/\[[xX]\]/g);
    
    return {
        total: totalMatch?.length || 0,
        completed: completedMatch?.length || 0
    };
}

describe('KiroSpecReader', () => {
    describe('determinePhase', () => {
        it('should return requirements when no files exist', () => {
            const phase = determinePhase(false, false, false);
            assert.strictEqual(phase, 'requirements');
        });

        it('should return design when only requirements exist', () => {
            const phase = determinePhase(true, false, false);
            assert.strictEqual(phase, 'design');
        });

        it('should return tasks when requirements and design exist', () => {
            const phase = determinePhase(true, true, false);
            assert.strictEqual(phase, 'tasks');
        });

        it('should return implementation when all files exist', () => {
            const phase = determinePhase(true, true, true);
            assert.strictEqual(phase, 'implementation');
        });

        it('should return complete when all tasks done', () => {
            const phase = determinePhase(true, true, true, { completed: 5, total: 5 });
            assert.strictEqual(phase, 'complete');
        });

        it('should remain implementation if not all tasks done', () => {
            const phase = determinePhase(true, true, true, { completed: 3, total: 5 });
            assert.strictEqual(phase, 'implementation');
        });

        it('should not be complete if zero tasks', () => {
            const phase = determinePhase(true, true, true, { completed: 0, total: 0 });
            assert.strictEqual(phase, 'implementation');
        });
    });

    describe('parseTaskProgress', () => {
        it('should count empty checkboxes', () => {
            const content = `- [ ] Task 1
- [ ] Task 2
- [ ] Task 3`;
            const progress = parseTaskProgress(content);
            
            assert.strictEqual(progress.total, 3);
            assert.strictEqual(progress.completed, 0);
        });

        it('should count completed checkboxes (lowercase x)', () => {
            const content = `- [x] Done 1
- [x] Done 2`;
            const progress = parseTaskProgress(content);
            
            assert.strictEqual(progress.total, 2);
            assert.strictEqual(progress.completed, 2);
        });

        it('should count completed checkboxes (uppercase X)', () => {
            const content = `- [X] Done 1
- [X] Done 2`;
            const progress = parseTaskProgress(content);
            
            assert.strictEqual(progress.completed, 2);
        });

        it('should count mixed statuses', () => {
            const content = `- [x] Done
- [ ] Not done
- [X] Also done
- [/] In progress`;
            const progress = parseTaskProgress(content);
            
            assert.strictEqual(progress.total, 4);
            assert.strictEqual(progress.completed, 2);
        });

        it('should handle content without checkboxes', () => {
            const content = `# Tasks
Some description here`;
            const progress = parseTaskProgress(content);
            
            assert.strictEqual(progress.total, 0);
            assert.strictEqual(progress.completed, 0);
        });
    });

    describe('phase order', () => {
        it('should have correct phase ordering', () => {
            const phaseOrder: SDDPhase[] = ['requirements', 'design', 'tasks', 'implementation', 'complete'];
            
            assert.strictEqual(phaseOrder.indexOf('requirements'), 0);
            assert.strictEqual(phaseOrder.indexOf('design'), 1);
            assert.strictEqual(phaseOrder.indexOf('tasks'), 2);
            assert.strictEqual(phaseOrder.indexOf('implementation'), 3);
            assert.strictEqual(phaseOrder.indexOf('complete'), 4);
        });
    });
});
