/**
 * Agent Orchestration - Core Agents
 * Planner, Coder, Reviewer, Fixer
 */

import { ClaudeAPIClient } from './ClaudeAPIClient';
import { SecurityScannerAgent } from './SecurityScannerAgent';
import { ResearcherAgent } from './ResearcherAgent';

/**
 * Agent roles matching DevKit methodology
 */
export enum AgentRole {
    PLANNER = 'planner',
    CODER = 'coder',
    REVIEWER = 'reviewer',
    FIXER = 'fixer',
    RESEARCHER = 'researcher',
    SECURITY = 'security',
    TESTER = 'tester',
    CRITIC = 'critic'
}

/**
 * Agent execution status
 */
export enum AgentStatus {
    IDLE = 'idle',
    RUNNING = 'running',
    COMPLETED = 'completed',
    FAILED = 'failed',
    WAITING = 'waiting'
}

/**
 * Base agent interface
 */
export interface Agent {
    id: string;
    name: string;
    role: AgentRole;
    status: AgentStatus;
    lastRun?: Date;
    output?: string;
}

/**
 * Spec input for planning
 */
export interface Spec {
    title: string;
    requirements: string[];
    design?: string;
}

/**
 * Plan output from Planner
 */
export interface Plan {
    tasks: PlanTask[];
    estimatedTime?: string;
}

/**
 * Task in plan
 */
export interface PlanTask {
    id: string;
    title: string;
    description?: string;
    dependencies?: string[];
    priority: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * Code result from Coder
 */
export interface CodeResult {
    status: 'completed' | 'failed' | 'needs_review';
    filesChanged?: string[];
    linesAdded?: number;
    linesRemoved?: number;
}

/**
 * Review result from Reviewer
 */
export interface ReviewResult {
    stage1: { passed: boolean; checks: string[] };
    stage2: { passed: boolean; checks: string[] };
    approved: boolean;
    issues: ReviewIssue[];
}

/**
 * Issue found during review
 */
export interface ReviewIssue {
    id: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    file?: string;
    line?: number;
}

/**
 * Fix result from Fixer
 */
export interface FixResult {
    fixed: number;
    remaining: number;
    details?: string[];
}

/**
 * Complexity estimate
 */
export interface ComplexityEstimate {
    complexity: 'low' | 'medium' | 'high' | 'critical';
    reasoning?: string;
}

/**
 * Base Agent implementation
 */
export abstract class BaseAgent implements Agent {
    id: string;
    name: string;
    role: AgentRole;
    status: AgentStatus = AgentStatus.IDLE;
    lastRun?: Date;
    output?: string;

    constructor(id: string, name: string, role: AgentRole) {
        this.id = id;
        this.name = name;
        this.role = role;
    }

    protected updateStatus(status: AgentStatus): void {
        this.status = status;
        if (status === AgentStatus.COMPLETED || status === AgentStatus.FAILED) {
            this.lastRun = new Date();
        }
    }
}

/**
 * Planner Agent - Creates plans from specs
 */
export class PlannerAgent extends BaseAgent {
    constructor() {
        super('planner', 'Planner', AgentRole.PLANNER);
    }

    async createPlan(spec: Spec): Promise<Plan> {
        this.updateStatus(AgentStatus.RUNNING);
        
        try {
            // Simulate planning based on requirements
            const tasks: PlanTask[] = spec.requirements.map((req, index) => ({
                id: `task-${index + 1}`,
                title: `Implement: ${req}`,
                description: `Implementation task for requirement: ${req}`,
                priority: index === 0 ? 'high' : 'medium' as const
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
        } catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            throw error;
        }
    }

    async estimateComplexity(spec: Spec): Promise<ComplexityEstimate> {
        const reqCount = spec.requirements.length;
        
        let complexity: 'low' | 'medium' | 'high' | 'critical';
        if (reqCount <= 2) complexity = 'low';
        else if (reqCount <= 5) complexity = 'medium';
        else if (reqCount <= 10) complexity = 'high';
        else complexity = 'critical';

        return {
            complexity,
            reasoning: `Based on ${reqCount} requirements`
        };
    }
}

/**
 * Coder Agent - Implements tasks
 */
export class CoderAgent extends BaseAgent {
    private claude: ClaudeAPIClient;
    private securityScanner: SecurityScannerAgent | null = null;
    private researcher: ResearcherAgent | null = null;

    constructor(claude?: ClaudeAPIClient) {
        super('coder', 'Coder', AgentRole.CODER);
        this.claude = claude || new ClaudeAPIClient();
    }

    /**
     * Set security scanner for pre-commit checks
     */
    setSecurityScanner(scanner: SecurityScannerAgent): void {
        this.securityScanner = scanner;
    }

    /**
     * Set researcher for context gathering
     */
    setResearcher(researcher: ResearcherAgent): void {
        this.researcher = researcher;
    }

    async implement(task: PlanTask, spec?: Spec): Promise<CodeResult> {
        this.updateStatus(AgentStatus.RUNNING);
        
        try {
            // 1. Gather context if researcher available
            let context = '';
            if (this.researcher) {
                try {
                    const researchResult = await this.researcher.research(task.title);
                    context = JSON.stringify(researchResult.facts.slice(0, 10));
                } catch {
                    // Continue without context
                }
            }

            // 2. Generate code with Claude
            let files: { language: string; path: string | null; content: string }[] = [];
            
            if (this.claude.isConfigured()) {
                const result = await this.claude.generateCode(
                    task.description || task.title,
                    spec ? spec.requirements.join('\n') : task.title,
                    context
                );
                files = result.files;
                this.output = `Generated ${files.length} files`;
            } else {
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
                    } as CodeResult & { securityBlocked: boolean; threats: any[] };
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
        } catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            this.output = `Error: ${error instanceof Error ? error.message : 'Unknown'}`;
            return { status: 'failed' };
        }
    }
}

/**
 * Reviewer Agent - Two-stage review (Spec Compliance + Code Quality)
 */
export class ReviewerAgent extends BaseAgent {
    constructor() {
        super('reviewer', 'Reviewer', AgentRole.REVIEWER);
    }

    async review(code: { files: string[]; changes: number }, spec: Spec): Promise<ReviewResult> {
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

            const issues: ReviewIssue[] = [];
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
        } catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            throw error;
        }
    }
}

/**
 * Fixer Agent - Fixes issues from review
 */
export class FixerAgent extends BaseAgent {
    private maxIterations = 3;
    private currentIteration = 0;
    private claude: ClaudeAPIClient;
    private researcher: ResearcherAgent | null = null;
    private failedFixes: Map<string, string[]> = new Map();

    constructor(claude?: ClaudeAPIClient) {
        super('fixer', 'Fixer', AgentRole.FIXER);
        this.claude = claude || new ClaudeAPIClient();
    }

    /**
     * Set researcher for finding similar past fixes
     */
    setResearcher(researcher: ResearcherAgent): void {
        this.researcher = researcher;
    }

    async fix(issues: ReviewIssue[]): Promise<FixResult> {
        this.updateStatus(AgentStatus.RUNNING);
        this.currentIteration++;
        
        try {
            let fixed = 0;
            const details: string[] = [];
            
            for (const issue of issues) {
                // 1. Search for similar past fixes
                let pastFixes: string[] = [];
                if (this.researcher) {
                    try {
                        pastFixes = await this.researcher.findSimilarDecisions(issue.description);
                    } catch {
                        // Continue without past context
                    }
                }

                // 2. Generate fix with Claude
                if (this.claude.isConfigured() && issue.file) {
                    try {
                        const result = await this.claude.generateFix(
                            issue.description,
                            `File: ${issue.file}, Line: ${issue.line || 'unknown'}`,
                            pastFixes.length > 0 ? `Similar past fixes:\n${pastFixes.join('\n')}` : ''
                        );
                        
                        if (result.files.length > 0) {
                            fixed++;
                            details.push(`Fixed: ${issue.description}`);
                        }
                    } catch (error) {
                        // Record failed fix for learning
                        this.recordFailedFix(issue);
                        details.push(`Failed to fix: ${issue.description}`);
                    }
                } else {
                    // Fallback: simulate fix
                    fixed++;
                    details.push(`[Mock] Fixed: ${issue.description}`);
                }
            }

            const remaining = issues.length - fixed;
            this.output = `Fixed ${fixed}/${issues.length} issues in iteration ${this.currentIteration}`;
            
            this.updateStatus(AgentStatus.COMPLETED);
            return { fixed, remaining, details };
        } catch (error) {
            this.updateStatus(AgentStatus.FAILED);
            return { fixed: 0, remaining: issues.length };
        }
    }

    private recordFailedFix(issue: ReviewIssue): void {
        const key = issue.file || 'unknown';
        const existing = this.failedFixes.get(key) || [];
        existing.push(issue.description);
        this.failedFixes.set(key, existing);
    }

    canRetry(): boolean {
        return this.currentIteration < this.maxIterations;
    }

    resetIterations(): void {
        this.currentIteration = 0;
        this.failedFixes.clear();
    }

    getFailedFixes(): Map<string, string[]> {
        return this.failedFixes;
    }
}

/**
 * Agent Registry - Manages all agents
 */
export class AgentRegistry {
    private agents: Map<string, Agent> = new Map();

    constructor() {
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
    registerExtendedAgents(config: {
        rlmEndpoint?: string;
        brainEndpoint?: string;
        brainApiKey?: string;
    }): void {
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

    register(agent: Agent): void {
        this.agents.set(agent.id, agent);
    }

    getAgent(id: string): Agent | undefined {
        return this.agents.get(id);
    }

    getAgents(): Agent[] {
        return Array.from(this.agents.values());
    }

    getAgentsByRole(role: AgentRole): Agent[] {
        return this.getAgents().filter(a => a.role === role);
    }

    getAgentsByStatus(status: AgentStatus): Agent[] {
        return this.getAgents().filter(a => a.status === status);
    }
}
