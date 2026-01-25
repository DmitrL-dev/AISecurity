/**
 * QA Loop Tests
 * TDD: Tests first
 */

import * as assert from 'assert';
import { QALoop, QAIteration, QAStatus } from '../qa/QALoop';

suite('QA Loop Test Suite', () => {

    test('QA Loop should initialize with max iterations', () => {
        const loop = new QALoop(3);
        
        assert.strictEqual(loop.maxIterations, 3);
        assert.strictEqual(loop.currentIteration, 0);
        assert.strictEqual(loop.status, QAStatus.PENDING);
    });

    test('QA Loop should run iteration', async () => {
        const loop = new QALoop(3);
        
        const result = await loop.runIteration({
            code: { files: ['test.ts'] },
            spec: { title: 'Test', requirements: ['Req 1'] }
        });
        
        assert.strictEqual(loop.currentIteration, 1);
        assert.ok(result.review, 'Should have review result');
    });

    test('QA Loop should track issues across iterations', async () => {
        const loop = new QALoop(3);
        
        // Simulate finding issues
        loop.addIssue({ id: '1', severity: 'high', description: 'Bug 1' });
        loop.addIssue({ id: '2', severity: 'medium', description: 'Bug 2' });
        
        assert.strictEqual(loop.getOpenIssues().length, 2);
        
        // Mark one as fixed
        loop.markFixed('1');
        
        assert.strictEqual(loop.getOpenIssues().length, 1);
        assert.strictEqual(loop.getFixedIssues().length, 1);
    });

    test('QA Loop should complete when all issues fixed', async () => {
        const loop = new QALoop(3);
        
        loop.addIssue({ id: '1', severity: 'low', description: 'Minor bug' });
        loop.markFixed('1');
        
        const canComplete = loop.canComplete();
        assert.ok(canComplete, 'Should be able to complete when no open issues');
    });

    test('QA Loop should reach max iterations', async () => {
        const loop = new QALoop(2);
        
        // Add persistent issue
        loop.addIssue({ id: '1', severity: 'critical', description: 'Unfixable' });
        
        await loop.runIteration({ code: { files: [] }, spec: { title: '', requirements: [] } });
        await loop.runIteration({ code: { files: [] }, spec: { title: '', requirements: [] } });
        
        // After max iterations, currentIteration should equal maxIterations
        assert.strictEqual(loop.currentIteration, 2);
        assert.strictEqual(loop.currentIteration >= loop.maxIterations, true);
    });

    test('QA Loop should approve when passing', async () => {
        const loop = new QALoop(3);
        
        // No issues = approval
        const approved = await loop.approve();
        
        assert.ok(approved, 'Should approve when no open issues');
        assert.strictEqual(loop.status, QAStatus.APPROVED);
    });

    test('QA Loop should track iteration history', async () => {
        const loop = new QALoop(3);
        
        await loop.runIteration({ code: { files: ['a.ts'] }, spec: { title: 'A', requirements: [] } });
        await loop.runIteration({ code: { files: ['b.ts'] }, spec: { title: 'B', requirements: [] } });
        
        const history = loop.getHistory();
        
        assert.strictEqual(history.length, 2);
        assert.ok(history[0].timestamp, 'Should have timestamp');
    });
});
