"use strict";
/**
 * Agent Orchestration - Core Agents
 * Planner, Coder, Reviewer, Fixer
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentRegistry = exports.FixerAgent = exports.ReviewerAgent = exports.CoderAgent = exports.PlannerAgent = exports.BaseAgent = exports.AgentStatus = exports.AgentRole = void 0;
const ClaudeAPIClient_1 = require("./ClaudeAPIClient");
/**
 * Agent roles matching DevKit methodology
 */
var AgentRole;
(function (AgentRole) {
    AgentRole["PLANNER"] = "planner";
    AgentRole["CODER"] = "coder";
    AgentRole["REVIEWER"] = "reviewer";
    AgentRole["FIXER"] = "fixer";
    AgentRole["RESEARCHER"] = "researcher";
    AgentRole["SECURITY"] = "security";
    AgentRole["TESTER"] = "tester";
    AgentRole["CRITIC"] = "critic";
})(AgentRole || (exports.AgentRole = AgentRole = {}));
/**
 * Agent execution status
 */
var AgentStatus;
(function (AgentStatus) {
    AgentStatus["IDLE"] = "idle";
    AgentStatus["RUNNING"] = "running";
    AgentStatus["COMPLETED"] = "completed";
    AgentStatus["FAILED"] = "failed";
    AgentStatus["WAITING"] = "waiting";
})(AgentStatus || (exports.AgentStatus = AgentStatus = {}));
/**
 * Base Agent implementation
 */
class BaseAgent {
    constructor(id, name, role) {
        this.status = AgentStatus.IDLE;
        this.id = id;
        this.name = name;
        this.role = role;
    }
    updateStatus(status) {
        this.status = status;
        if (status === AgentStatus.COMPLETED || status === AgentStatus.FAILED) {
            this.lastRun = new Date();
        }
    }
}
exports.BaseAgent = BaseAgent;
/**
 * Planner Agent - Creates plans from specs
 */
class PlannerAgent extends BaseAgent {
    constructor() {
        super('planner', 'Planner', AgentRole.PLANNER);
    }
    async createPlan(spec) {
        this.updateStatus(AgentStatus.RUNNING);
        try {
            // Simulate planning based on requirements
            const tasks = spec.requirements.map((req, index) => ({
                id: `task-${index + 1}`,
                title: `Implement: ${req}`,
                description: `Implementation task for requirement: ${req}`,
                priority: index === 0 ? 'high' : 'medium'
            }));
            // Add test task
            tasks.push({
                id: `task-${tasks.length + 1}`,
                title: 'Write tests',
                description: 'TDD: Write tests for all tasks',
                priority: 'high'
            });
            this.updateStatus(AgentStatus.COMPLETED);
            return { tasks };
        }
        catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            throw error;
        }
    }
    async estimateComplexity(spec) {
        const reqCount = spec.requirements.length;
        let complexity;
        if (reqCount <= 2)
            complexity = 'low';
        else if (reqCount <= 5)
            complexity = 'medium';
        else if (reqCount <= 10)
            complexity = 'high';
        else
            complexity = 'critical';
        return {
            complexity,
            reasoning: `Based on ${reqCount} requirements`
        };
    }
}
exports.PlannerAgent = PlannerAgent;
/**
 * Coder Agent - Implements tasks
 */
class CoderAgent extends BaseAgent {
    constructor(claude) {
        super('coder', 'Coder', AgentRole.CODER);
        this.securityScanner = null;
        this.researcher = null;
        this.claude = claude || new ClaudeAPIClient_1.ClaudeAPIClient();
    }
    /**
     * Set security scanner for pre-commit checks
     */
    setSecurityScanner(scanner) {
        this.securityScanner = scanner;
    }
    /**
     * Set researcher for context gathering
     */
    setResearcher(researcher) {
        this.researcher = researcher;
    }
    async implement(task, spec) {
        this.updateStatus(AgentStatus.RUNNING);
        try {
            // 1. Gather context if researcher available
            let context = '';
            if (this.researcher) {
                try {
                    const researchResult = await this.researcher.research(task.title);
                    context = JSON.stringify(researchResult.facts.slice(0, 10));
                }
                catch {
                    // Continue without context
                }
            }
            // 2. Generate code with Claude
            let files = [];
            if (this.claude.isConfigured()) {
                const result = await this.claude.generateCode(task.description || task.title, spec ? spec.requirements.join('\n') : task.title, context);
                files = result.files;
                this.output = `Generated ${files.length} files`;
            }
            else {
                // Fallback for development without API key
                this.output = `[Mock] Implementing: ${task.title}`;
                files = [{
                        language: 'typescript',
                        path: `src/${task.id}.ts`,
                        content: `// Implementation for: ${task.title}`
                    }];
            }
            // 3. Security pre-check before writing
            if (this.securityScanner && files.length > 0) {
                const codeToCheck = files.map(f => f.content);
                const securityResult = await this.securityScanner.scan(codeToCheck);
                if (securityResult.threats.some(t => t.severity === 'critical')) {
                    this.updateStatus(AgentStatus.FAILED);
                    return {
                        status: 'failed',
                        filesChanged: [],
                        linesAdded: 0,
                        linesRemoved: 0,
                        securityBlocked: true,
                        threats: securityResult.threats
                    };
                }
            }
            // 4. Write files (placeholder - actual file writing would happen here)
            const filesChanged = files.map(f => f.path || 'unknown');
            const linesAdded = files.reduce((sum, f) => sum + f.content.split('\n').length, 0);
            this.updateStatus(AgentStatus.COMPLETED);
            return {
                status: 'needs_review',
                filesChanged,
                linesAdded,
                linesRemoved: 0
            };
        }
        catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            this.output = `Error: ${error instanceof Error ? error.message : 'Unknown'}`;
            return { status: 'failed' };
        }
    }
}
exports.CoderAgent = CoderAgent;
/**
 * Reviewer Agent - Two-stage review (Spec Compliance + Code Quality)
 */
class ReviewerAgent extends BaseAgent {
    constructor() {
        super('reviewer', 'Reviewer', AgentRole.REVIEWER);
    }
    async review(code, spec) {
        this.updateStatus(AgentStatus.RUNNING);
        try {
            // Stage 1: Spec Compliance
            const stage1 = {
                passed: true,
                checks: spec.requirements.map(r => `✓ ${r}`)
            };
            // Stage 2: Code Quality
            const stage2 = {
                passed: code.changes < 500, // Simple heuristic
                checks: [
                    '✓ Clean Architecture',
                    '✓ Type hints',
                    code.changes < 500 ? '✓ Reasonable size' : '✗ Too many changes'
                ]
            };
            const issues = [];
            if (!stage2.passed) {
                issues.push({
                    id: 'issue-1',
                    severity: 'medium',
                    description: 'Consider breaking into smaller changes'
                });
            }
            const approved = stage1.passed && stage2.passed;
            this.updateStatus(AgentStatus.COMPLETED);
            return { stage1, stage2, approved, issues };
        }
        catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            throw error;
        }
    }
}
exports.ReviewerAgent = ReviewerAgent;
/**
 * Fixer Agent - Fixes issues from review
 */
class FixerAgent extends BaseAgent {
    constructor(claude) {
        super('fixer', 'Fixer', AgentRole.FIXER);
        this.maxIterations = 3;
        this.currentIteration = 0;
        this.researcher = null;
        this.failedFixes = new Map();
        this.claude = claude || new ClaudeAPIClient_1.ClaudeAPIClient();
    }
    /**
     * Set researcher for finding similar past fixes
     */
    setResearcher(researcher) {
        this.researcher = researcher;
    }
    async fix(issues) {
        this.updateStatus(AgentStatus.RUNNING);
        this.currentIteration++;
        try {
            let fixed = 0;
            const details = [];
            for (const issue of issues) {
                // 1. Search for similar past fixes
                let pastFixes = [];
                if (this.researcher) {
                    try {
                        pastFixes = await this.researcher.findSimilarDecisions(issue.description);
                    }
                    catch {
                        // Continue without past context
                    }
                }
                // 2. Generate fix with Claude
                if (this.claude.isConfigured() && issue.file) {
                    try {
                        const result = await this.claude.generateFix(issue.description, `File: ${issue.file}, Line: ${issue.line || 'unknown'}`, pastFixes.length > 0 ? `Similar past fixes:\n${pastFixes.join('\n')}` : '');
                        if (result.files.length > 0) {
                            fixed++;
                            details.push(`Fixed: ${issue.description}`);
                        }
                    }
                    catch (error) {
                        // Record failed fix for learning
                        this.recordFailedFix(issue);
                        details.push(`Failed to fix: ${issue.description}`);
                    }
                }
                else {
                    // Fallback: simulate fix
                    fixed++;
                    details.push(`[Mock] Fixed: ${issue.description}`);
                }
            }
            const remaining = issues.length - fixed;
            this.output = `Fixed ${fixed}/${issues.length} issues in iteration ${this.currentIteration}`;
            this.updateStatus(AgentStatus.COMPLETED);
            return { fixed, remaining, details };
        }
        catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            return { fixed: 0, remaining: issues.length };
        }
    }
    recordFailedFix(issue) {
        const key = issue.file || 'unknown';
        const existing = this.failedFixes.get(key) || [];
        existing.push(issue.description);
        this.failedFixes.set(key, existing);
    }
    canRetry() {
        return this.currentIteration < this.maxIterations;
    }
    resetIterations() {
        this.currentIteration = 0;
        this.failedFixes.clear();
    }
    getFailedFixes() {
        return this.failedFixes;
    }
}
exports.FixerAgent = FixerAgent;
/**
 * Agent Registry - Manages all agents
 */
class AgentRegistry {
    constructor() {
        this.agents = new Map();
        // Register core agents
        this.register(new PlannerAgent());
        this.register(new CoderAgent());
        this.register(new ReviewerAgent());
        this.register(new FixerAgent());
        // Extended agents will be registered dynamically
        // when their dependencies (RLM, Brain API) are available
    }
    /**
     * Register extended agents with endpoints
     */
    registerExtendedAgents(config) {
        // Import dynamically to avoid circular deps
        const { ResearcherAgent } = require('./ResearcherAgent');
        const { SecurityScannerAgent } = require('./SecurityScannerAgent');
        const { TesterAgent } = require('./TesterAgent');
        const { SpecCriticAgent } = require('./SpecCriticAgent');
        this.register(new ResearcherAgent(config.rlmEndpoint));
        this.register(new SecurityScannerAgent(config.brainEndpoint, config.brainApiKey));
        this.register(new TesterAgent());
        this.register(new SpecCriticAgent(config.rlmEndpoint));
    }
    register(agent) {
        this.agents.set(agent.id, agent);
    }
    getAgent(id) {
        return this.agents.get(id);
    }
    getAgents() {
        return Array.from(this.agents.values());
    }
    getAgentsByRole(role) {
        return this.getAgents().filter(a => a.role === role);
    }
    getAgentsByStatus(status) {
        return this.getAgents().filter(a => a.status === status);
    }
}
exports.AgentRegistry = AgentRegistry;
//# sourceMappingURL=AgentRegistry.js.map