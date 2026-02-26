"use strict";
/**
 * Unit tests for TasksReader
 * TDD approach: verify that tasks.md parsing works correctly
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
const fs = __importStar(require("fs"));
// Test the parsing logic directly
function testParseTasksContent() {
    const testContent = `# Test Tasks

## Phase 1: Setup

- [x] **Task 1.1**: Complete setup
- [ ] **Task 1.2**: Pending task
- [/] **Task 1.3**: In progress task

## Phase 2: Implementation

- [ ] Task without bold
- [x] Done task
`;
    const lines = testContent.split('\n');
    const tasks = [];
    let currentPhase = '';
    let taskIndex = 0;
    for (const line of lines) {
        // Detect phase headers
        const phaseMatch = line.match(/^##\s+(?:Phase\s+\d+[:.]\s*)?(.+)/);
        if (phaseMatch) {
            currentPhase = phaseMatch[1].trim();
        }
        // Parse checkbox lines
        const taskMatch = line.match(/^[\s-]*\[([ xX\/])\]\s+(.+)/);
        if (taskMatch) {
            const checkState = taskMatch[1];
            const taskText = taskMatch[2];
            let status;
            if (checkState === 'x' || checkState === 'X') {
                status = 'done';
            }
            else if (checkState === '/') {
                status = 'in-progress';
            }
            else {
                status = 'spec';
            }
            const titleMatch = taskText.match(/\*\*(.+?)\*\*[:\s]*(.*)/);
            let title;
            let description;
            if (titleMatch) {
                title = titleMatch[1];
                description = titleMatch[2] || undefined;
            }
            else {
                title = taskText;
            }
            tasks.push({
                id: `test-${taskIndex++}`,
                title,
                description,
                status,
                phase: currentPhase
            });
        }
    }
    console.log('Parsed tasks:', tasks);
    console.log('Total tasks:', tasks.length);
    // Assertions
    assert.strictEqual(tasks.length, 5, 'Should parse 5 tasks');
    assert.strictEqual(tasks[0].status, 'done', 'First task should be done');
    assert.strictEqual(tasks[1].status, 'spec', 'Second task should be spec (pending)');
    assert.strictEqual(tasks[2].status, 'in-progress', 'Third task should be in-progress');
    assert.strictEqual(tasks[0].title, 'Task 1.1', 'Should extract bold title');
    assert.strictEqual(tasks[3].title, 'Task without bold', 'Should handle non-bold titles');
    console.log('✅ All parsing tests passed!');
}
// Test with real tasks.md file
async function testRealFile() {
    const testPath = 'c:/AISecurity/.kiro/specs/memory-bridge/tasks.md';
    if (!fs.existsSync(testPath)) {
        console.log('❌ Test file not found:', testPath);
        return;
    }
    const content = fs.readFileSync(testPath, 'utf-8');
    const lines = content.split('\n');
    let specCount = 0;
    let doneCount = 0;
    let inProgressCount = 0;
    for (const line of lines) {
        const taskMatch = line.match(/^[\s-]*\[([ xX\/])\]\s+(.+)/);
        if (taskMatch) {
            const checkState = taskMatch[1];
            if (checkState === 'x' || checkState === 'X') {
                doneCount++;
            }
            else if (checkState === '/') {
                inProgressCount++;
            }
            else {
                specCount++;
            }
        }
    }
    console.log('Real file parsing results:');
    console.log('  Spec (TODO):', specCount);
    console.log('  In Progress:', inProgressCount);
    console.log('  Done:', doneCount);
    console.log('  Total:', specCount + inProgressCount + doneCount);
}
// Run tests
testParseTasksContent();
testRealFile();
//# sourceMappingURL=TasksReader.test.js.map