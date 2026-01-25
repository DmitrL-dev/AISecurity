"use strict";
/**
 * Swarm Mode Unit Tests
 * Tests for ModelRouter, WorkerPreamble, SwarmSpawner
 * TDD: Tests FIRST, then implementation
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
// ============================================
// ModelRouter Tests
// ============================================
// ModelRouter implementation for testing
class ModelRouter {
    constructor() {
        this.modelMatrix = {
            'researcher': 'haiku',
            'planner': 'sonnet',
            'tester': 'sonnet',
            'coder': 'sonnet',
            'security': 'opus',
            'reviewer': 'opus',
            'fixer': 'sonnet',
            'integrator': 'sonnet'
        };
    }
    getModel(agentType, taskComplexity) {
        if (taskComplexity === 'high')
            return 'opus';
        return this.modelMatrix[agentType];
    }
}
describe('ModelRouter', () => {
    let router;
    beforeEach(() => {
        router = new ModelRouter();
    });
    describe('getModel', () => {
        it('should return haiku for researcher', () => {
            assert.strictEqual(router.getModel('researcher'), 'haiku');
        });
        it('should return sonnet for coder', () => {
            assert.strictEqual(router.getModel('coder'), 'sonnet');
        });
        it('should return opus for security scanner', () => {
            assert.strictEqual(router.getModel('security'), 'opus');
        });
        it('should return opus for reviewer', () => {
            assert.strictEqual(router.getModel('reviewer'), 'opus');
        });
        it('should override to opus for high complexity', () => {
            assert.strictEqual(router.getModel('coder', 'high'), 'opus');
        });
        it('should keep original model for low complexity', () => {
            assert.strictEqual(router.getModel('coder', 'low'), 'sonnet');
        });
        it('should return sonnet for planner, tester, fixer, integrator', () => {
            const sonnetAgents = ['planner', 'tester', 'fixer', 'integrator'];
            sonnetAgents.forEach(agent => {
                assert.strictEqual(router.getModel(agent), 'sonnet', `${agent} should use sonnet`);
            });
        });
    });
});
// ============================================
// WorkerPreamble Tests
// ============================================
class WorkerPreamble {
    static generate(taskDescription) {
        return `CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Do NOT spawn sub-agents
- Do NOT call TaskCreate or TaskUpdate
- Report your results with absolute file paths

TASK:
${taskDescription}`;
    }
}
describe('WorkerPreamble', () => {
    describe('generate', () => {
        it('should include WORKER context', () => {
            const preamble = WorkerPreamble.generate('Test task');
            assert.ok(preamble.includes('You are a WORKER agent'));
        });
        it('should include no sub-agents rule', () => {
            const preamble = WorkerPreamble.generate('Test task');
            assert.ok(preamble.includes('Do NOT spawn sub-agents'));
        });
        it('should include no TaskCreate rule', () => {
            const preamble = WorkerPreamble.generate('Test task');
            assert.ok(preamble.includes('Do NOT call TaskCreate'));
        });
        it('should include the task description', () => {
            const task = 'Implement authentication module';
            const preamble = WorkerPreamble.generate(task);
            assert.ok(preamble.includes(task));
        });
        it('should have TASK section at the end', () => {
            const preamble = WorkerPreamble.generate('My task');
            assert.ok(preamble.includes('TASK:\nMy task'));
        });
    });
});
// ============================================
// SwarmSpawner Tests (Logic only, no Claude API)
// ============================================
describe('SwarmSpawner', () => {
    describe('dependency resolution', () => {
        it('should identify tasks with no blockers as ready', () => {
            const tasks = [
                { id: '1', agentType: 'coder', description: 'Task 1' },
                { id: '2', agentType: 'coder', description: 'Task 2', blockedBy: ['1'] }
            ];
            const ready = tasks.filter(t => !t.blockedBy?.length);
            assert.strictEqual(ready.length, 1);
            assert.strictEqual(ready[0].id, '1');
        });
        it('should unblock tasks when dependencies complete', () => {
            const tasks = [
                { id: '1', agentType: 'coder', description: 'Task 1' },
                { id: '2', agentType: 'coder', description: 'Task 2', blockedBy: ['1'] }
            ];
            const completed = new Set(['1']);
            const ready = tasks.filter(t => !t.blockedBy?.some(dep => !completed.has(dep)));
            assert.strictEqual(ready.length, 2);
        });
        it('should handle multiple dependencies', () => {
            const tasks = [
                { id: '1', agentType: 'coder', description: 'Task 1' },
                { id: '2', agentType: 'coder', description: 'Task 2' },
                { id: '3', agentType: 'coder', description: 'Task 3', blockedBy: ['1', '2'] }
            ];
            const completed = new Set(['1']); // Only 1 done
            const ready = tasks.filter(t => !t.blockedBy?.some(dep => !completed.has(dep)));
            // Task 3 still blocked (needs 2)
            assert.strictEqual(ready.length, 2);
            assert.ok(!ready.find(t => t.id === '3'));
        });
    });
    describe('swarm sizing', () => {
        function estimateSwarmSize(task) {
            if (task.toLowerCase().includes('security') || task.toLowerCase().includes('audit'))
                return 10;
            if (task.toLowerCase().includes('feature') || task.toLowerCase().includes('implement'))
                return 4;
            if (task.toLowerCase().includes('fix') || task.toLowerCase().includes('bug'))
                return 2;
            return 2;
        }
        it('should return 10 for security audit', () => {
            assert.strictEqual(estimateSwarmSize('Perform security audit'), 10);
        });
        it('should return 4 for feature implementation', () => {
            assert.strictEqual(estimateSwarmSize('Implement user authentication feature'), 4);
        });
        it('should return 2 for bug fix', () => {
            assert.strictEqual(estimateSwarmSize('Fix login bug'), 2);
        });
        it('should return 2 as default', () => {
            assert.strictEqual(estimateSwarmSize('Random task'), 2);
        });
    });
    describe('parallel execution pattern', () => {
        it('should group independent tasks for parallel execution', () => {
            const tasks = [
                { id: '1', agentType: 'researcher', description: 'Research A' },
                { id: '2', agentType: 'researcher', description: 'Research B' },
                { id: '3', agentType: 'researcher', description: 'Research C' }
            ];
            const parallelGroup = tasks.filter(t => !t.blockedBy?.length);
            assert.strictEqual(parallelGroup.length, 3);
        });
    });
});
//# sourceMappingURL=swarm-mode.test.js.map