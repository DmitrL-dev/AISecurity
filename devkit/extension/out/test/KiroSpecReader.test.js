"use strict";
/**
 * KiroSpecReader Unit Tests
 * Tests for spec phase detection and task progress parsing
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
// Phase detection logic (same as readSpecStatus)
function determinePhase(hasRequirements, hasDesign, hasTasks, taskProgress) {
    let phase = 'requirements';
    if (hasRequirements && !hasDesign) {
        phase = 'design';
    }
    else if (hasDesign && !hasTasks) {
        phase = 'tasks';
    }
    else if (hasTasks) {
        phase = 'implementation';
    }
    // Check if complete
    if (taskProgress && taskProgress.completed === taskProgress.total && taskProgress.total > 0) {
        phase = 'complete';
    }
    return phase;
}
// Task progress parsing (same as readTaskProgress)
function parseTaskProgress(content) {
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
            const phaseOrder = ['requirements', 'design', 'tasks', 'implementation', 'complete'];
            assert.strictEqual(phaseOrder.indexOf('requirements'), 0);
            assert.strictEqual(phaseOrder.indexOf('design'), 1);
            assert.strictEqual(phaseOrder.indexOf('tasks'), 2);
            assert.strictEqual(phaseOrder.indexOf('implementation'), 3);
            assert.strictEqual(phaseOrder.indexOf('complete'), 4);
        });
    });
});
//# sourceMappingURL=KiroSpecReader.test.js.map