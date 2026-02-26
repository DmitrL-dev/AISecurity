/**
 * Agent Orchestration Tests
 * TDD: Tests first, implementation after
 */

import * as assert from 'assert';
import { 
    Agent, 
    AgentRole, 
    AgentStatus, 
    AgentRegistry,
    PlannerAgent,
    CoderAgent,
    ReviewerAgent,
    FixerAgent
} from '../agents/AgentRegistry';

suite('Agent Interface Test Suite', () => {

    test('Agent should have required properties', () => {
        const registry = new AgentRegistry();
        const agents = registry.getAgents();
        
        assert.ok(agents.length > 0, 'Should have registered agents');
        
        const agent = agents[0];
        assert.ok(agent.id, 'Agent should have id');
        assert.ok(agent.name, 'Agent should have name');
        assert.ok(agent.role, 'Agent should have role');
        assert.ok(agent.status, 'Agent should have status');
    });

    test('AgentRegistry should have 4 core agents', () => {
        const registry = new AgentRegistry();
        const agents = registry.getAgents();
        
        const roles = agents.map(a => a.role);
        assert.ok(roles.includes(AgentRole.PLANNER), 'Should have Planner');
        assert.ok(roles.includes(AgentRole.CODER), 'Should have Coder');
        assert.ok(roles.includes(AgentRole.REVIEWER), 'Should have Reviewer');
        assert.ok(roles.includes(AgentRole.FIXER), 'Should have Fixer');
    });

    test('Agent should have initial IDLE status', () => {
        const registry = new AgentRegistry();
        const agent = registry.getAgent('planner');
        
        assert.strictEqual(agent?.status, AgentStatus.IDLE);
    });
});

suite('Planner Agent Test Suite', () => {

    test('Planner should create plan from spec', async () => {
        const planner = new PlannerAgent();
        const spec = {
            title: 'Add new feature',
            requirements: ['Req 1', 'Req 2']
        };
        
        const plan = await planner.createPlan(spec);
        
        assert.ok(plan.tasks, 'Plan should have tasks');
        assert.ok(plan.tasks.length > 0, 'Plan should have at least one task');
    });

    test('Planner should estimate complexity', async () => {
        const planner = new PlannerAgent();
        const spec = {
            title: 'Complex feature',
            requirements: ['DB changes', 'API endpoint', 'UI update', 'Tests']
        };
        
        const estimate = await planner.estimateComplexity(spec);
        
        assert.ok(estimate.complexity, 'Should have complexity rating');
        assert.ok(['low', 'medium', 'high', 'critical'].includes(estimate.complexity));
    });
});

suite('Coder Agent Test Suite', () => {

    test('Coder should implement task', async () => {
        const coder = new CoderAgent();
        const task = {
            id: '1',
            title: 'Implement function X',
            description: 'Create helper function',
            priority: 'medium' as const
        };
        
        const result = await coder.implement(task);
        
        assert.ok(result.status, 'Should have status');
        assert.ok(['completed', 'failed', 'needs_review'].includes(result.status));
    });
});

suite('Reviewer Agent Test Suite', () => {

    test('Reviewer should perform two-stage review', async () => {
        const reviewer = new ReviewerAgent();
        const code = { files: ['test.ts'], changes: 10 };
        const spec = { title: 'Test feature', requirements: ['Req 1'] };
        
        const review = await reviewer.review(code, spec);
        
        assert.ok(review.stage1, 'Should have stage 1 (spec compliance)');
        assert.ok(review.stage2, 'Should have stage 2 (code quality)');
        assert.ok(typeof review.approved === 'boolean', 'Should have approval status');
    });

    test('Reviewer should list issues', async () => {
        const reviewer = new ReviewerAgent();
        const code = { files: ['buggy.ts'], changes: 5 };
        const spec = { title: 'Test feature', requirements: ['Req 1'] };
        
        const review = await reviewer.review(code, spec);
        
        assert.ok(Array.isArray(review.issues), 'Should have issues array');
    });
});

suite('Fixer Agent Test Suite', () => {

    test('Fixer should fix issues', async () => {
        const fixer = new FixerAgent();
        const issues = [
            { id: '1', severity: 'high' as const, description: 'Missing test' }
        ];
        
        const result = await fixer.fix(issues);
        
        assert.ok(result.fixed >= 0, 'Should have fixed count');
        assert.ok(result.remaining >= 0, 'Should have remaining count');
    });
});

suite('Agent Orchestration Test Suite', () => {

    test('Should run full workflow: Plan → Code → Review → Fix', async () => {
        const registry = new AgentRegistry();
        
        const spec = { title: 'Test feature', requirements: ['Req 1'] };
        
        // Step 1: Plan
        const planner = registry.getAgent('planner') as PlannerAgent;
        const plan = await planner.createPlan(spec);
        assert.ok(plan.tasks.length > 0);
        
        // Step 2: Code
        const coder = registry.getAgent('coder') as CoderAgent;
        const codeResult = await coder.implement(plan.tasks[0]);
        assert.ok(codeResult.status);
        
        // Step 3: Review
        const reviewer = registry.getAgent('reviewer') as ReviewerAgent;
        const review = await reviewer.review({ files: [], changes: 0 }, spec);
        assert.ok(review.stage1);
        
        // Step 4: Fix if needed
        if (review.issues.length > 0) {
            const fixer = registry.getAgent('fixer') as FixerAgent;
            const fixResult = await fixer.fix(review.issues);
            assert.ok(fixResult.fixed >= 0);
        }
    });
});
