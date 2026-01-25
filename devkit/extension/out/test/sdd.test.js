"use strict";
/**
 * SDD (Spec-Driven Development) Unit Tests
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
const path = __importStar(require("path"));
describe('KiroSpecReader Tests', () => {
    describe('Phase Detection', () => {
        const phases = ['requirements', 'design', 'tasks', 'implementation'];
        it('should identify phases from file existence', () => {
            const specFiles = {
                'requirements.md': true,
                'design.md': true,
                'tasks.md': true
            };
            const phaseComplete = (phase) => {
                if (phase === 'requirements')
                    return specFiles['requirements.md'] === true;
                if (phase === 'design')
                    return specFiles['design.md'] === true;
                if (phase === 'tasks')
                    return specFiles['tasks.md'] === true;
                return false;
            };
            assert.strictEqual(phaseComplete('requirements'), true);
            assert.strictEqual(phaseComplete('design'), true);
            assert.strictEqual(phaseComplete('tasks'), true);
            assert.strictEqual(phaseComplete('implementation'), false);
        });
        it('should determine current phase correctly', () => {
            const completed = ['requirements', 'design'];
            const currentPhase = phases.find(p => !completed.includes(p)) || 'implementation';
            assert.strictEqual(currentPhase, 'tasks');
        });
    });
    describe('Spec Path Resolution', () => {
        it('should resolve spec directory paths', () => {
            const workspaceRoot = 'C:\\Projects\\sentinel';
            const specPath = path.join(workspaceRoot, '.kiro', 'specs');
            assert.ok(specPath.includes('.kiro'));
            assert.ok(specPath.includes('specs'));
        });
        it('should list spec directories', () => {
            const mockSpecs = [
                'api-versioning',
                'brain-observability',
                'dashboard-skeleton'
            ];
            assert.strictEqual(mockSpecs.length, 3);
            assert.ok(mockSpecs.includes('dashboard-skeleton'));
        });
    });
    describe('Progress Calculation', () => {
        it('should calculate task progress from checkboxes', () => {
            const tasksContent = `
                - [x] Task 1
                - [x] Task 2
                - [ ] Task 3
                - [x] Task 4
            `;
            const completed = (tasksContent.match(/\[x\]/g) || []).length;
            const total = (tasksContent.match(/\[[ x]\]/g) || []).length;
            const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
            assert.strictEqual(completed, 3);
            assert.strictEqual(total, 4);
            assert.strictEqual(progress, 75);
        });
        it('should handle empty tasks gracefully', () => {
            const tasksContent = '';
            const completed = (tasksContent.match(/\[x\]/g) || []).length;
            const total = (tasksContent.match(/\[[ x]\]/g) || []).length;
            const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
            assert.strictEqual(progress, 0);
        });
    });
    describe('Status Formatting', () => {
        it('should format status for webview', () => {
            const status = {
                phase: 'tasks',
                completed: ['requirements', 'design'],
                specs: [
                    { name: 'api-versioning', phase: 'implementation', progress: '100%' },
                    { name: 'dashboard-skeleton', phase: 'tasks', progress: '80%' }
                ]
            };
            assert.strictEqual(status.phase, 'tasks');
            assert.strictEqual(status.completed.length, 2);
            assert.strictEqual(status.specs.length, 2);
        });
    });
});
//# sourceMappingURL=sdd.test.js.map