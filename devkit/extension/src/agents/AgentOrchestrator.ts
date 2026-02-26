/**
 * Agent Orchestrator
 * Manages autonomous pipeline execution for 24/7 operation
 */

import { EventEmitter } from 'events';
import { 
    AgentRegistry, 
    AgentRole, 
    AgentStatus,
    PlannerAgent,
    CoderAgent,
    ReviewerAgent,
    FixerAgent,
    Spec,
    Plan,
    PlanTask
} from './AgentRegistry';
import { ResearcherAgent, ProjectContext } from './ResearcherAgent';
import { SecurityScannerAgent, SecurityResult } from './SecurityScannerAgent';
import { TesterAgent, TestSuite, TestResult } from './TesterAgent';
import { SpecCriticAgent, CritiqueResult } from './SpecCriticAgent';

/**
 * Orchestrator configuration
 */
export interface OrchestratorConfig {
    maxRuntime: number;           // Max runtime in ms
    checkpointInterval: number;   // Checkpoint every N ms
    maxFixIterations: number;     // Max fixer loops
    allowedOperations: {
        createFiles: boolean;
        modifyFiles: boolean;
        deleteFiles: boolean;
        runCommands: string[];
        gitOperations: string[];
    };
    endpoints: {
        rlm?: string;
        brain?: string;
        brainApiKey?: string;
    };
}

/**
 * Pipeline execution state
 */
export interface PipelineState {
    status: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'escalated';
    currentPhase: PipelinePhase;
    currentAgent: string | null;
    startTime: Date | null;
    progress: number;            // 0-100
    tasksCompleted: number;
    tasksTotal: number;
    currentTask: string | null;
    lastCheckpoint: Date | null;
    logs: LogEntry[];
}

/**
 * Pipeline phases
 */
export type PipelinePhase = 
    | 'research'
    | 'planning'
    | 'critique'
    | 'testing'
    | 'coding'
    | 'security'
    | 'review'
    | 'fixing'
    | 'completed';

/**
 * Log entry
 */
export interface LogEntry {
    timestamp: Date;
    agent: string;
    level: 'info' | 'warn' | 'error' | 'success';
    message: string;
}

/**
 * Escalation event
 */
export interface EscalationEvent {
    type: 'test_failure' | 'security_critical' | 'build_broken' | 'fixer_loop' | 'memory_limit';
    description: string;
    context: any;
    timestamp: Date;
}

/**
 * Agent Orchestrator - Manages autonomous pipeline
 */
export class AgentOrchestrator extends EventEmitter {
    private config: OrchestratorConfig;
    private state: PipelineState;
    private registry: AgentRegistry;
    
    // Agents
    private researcher: ResearcherAgent;
    private planner: PlannerAgent;
    private critic: SpecCriticAgent;
    private tester: TesterAgent;
    private coder: CoderAgent;
    private security: SecurityScannerAgent;
    private reviewer: ReviewerAgent;
    private fixer: FixerAgent;
    
    // State
    private currentSpec: Spec | null = null;
    private currentPlan: Plan | null = null;
    private fixerIterations = 0;
    private checkpointTimer: NodeJS.Timeout | null = null;

    constructor(config: Partial<OrchestratorConfig> = {}) {
        super();
        
        this.config = {
            maxRuntime: 8 * 60 * 60 * 1000, // 8 hours
            checkpointInterval: 30 * 60 * 1000, // 30 minutes
            maxFixIterations: 3,
            allowedOperations: {
                createFiles: true,
                modifyFiles: true,
                deleteFiles: false,
                runCommands: ['npm test', 'npm run build', 'pytest'],
                gitOperations: ['commit', 'push']
            },
            endpoints: {},
            ...config
        };

        this.state = this.createInitialState();
        this.registry = new AgentRegistry();
        
        // Initialize agents
        this.researcher = new ResearcherAgent(this.config.endpoints.rlm);
        this.planner = new PlannerAgent();
        this.critic = new SpecCriticAgent(this.config.endpoints.rlm);
        this.tester = new TesterAgent();
        this.coder = new CoderAgent();
        this.security = new SecurityScannerAgent(
            this.config.endpoints.brain,
            this.config.endpoints.brainApiKey
        );
        this.reviewer = new ReviewerAgent();
        this.fixer = new FixerAgent();
    }

    /**
     * Start autonomous execution of a global task
     */
    async execute(task: string): Promise<PipelineState> {
        this.log('info', 'Orchestrator', `Starting autonomous execution: "${task}"`);
        
        this.state.status = 'running';
        this.state.startTime = new Date();
        this.startCheckpointTimer();

        try {
            // Phase 1: Research
            await this.executePhase('research', async () => {
                const context = await this.researcher.gatherContext(task);
                this.emit('context', context);
                return context;
            });

            // Phase 2: Planning
            const spec: Spec = { title: task, requirements: [task] };
            this.currentSpec = spec;
            
            await this.executePhase('planning', async () => {
                this.currentPlan = await this.planner.createPlan(spec);
                this.state.tasksTotal = this.currentPlan.tasks.length;
                this.emit('plan', this.currentPlan);
                return this.currentPlan;
            });

            // Phase 3: Critique
            await this.executePhase('critique', async () => {
                const critique = await this.critic.critique(spec);
                if (critique.verdict === 'rejected') {
                    throw new Error(`Spec rejected: ${critique.weaknesses.join(', ')}`);
                }
                this.emit('critique', critique);
                return critique;
            });

            // Phase 4-7: Execute each task
            for (const task of this.currentPlan!.tasks) {
                await this.executeTask(task);
                this.state.tasksCompleted++;
                this.updateProgress();
            }

            this.state.status = 'completed';
            this.state.currentPhase = 'completed';
            this.log('success', 'Orchestrator', 'Pipeline completed successfully');

        } catch (error: any) {
            this.state.status = 'failed';
            this.log('error', 'Orchestrator', `Pipeline failed: ${error.message}`);
            this.emit('error', error);
        } finally {
            this.stopCheckpointTimer();
        }

        return this.state;
    }

    /**
     * Execute a single task through the pipeline
     */
    private async executeTask(task: PlanTask): Promise<void> {
        this.state.currentTask = task.title;
        this.fixerIterations = 0;

        let passed = false;
        while (!passed && this.fixerIterations < this.config.maxFixIterations) {
            // Generate tests
            await this.executePhase('testing', async () => {
                return this.tester.generateTests(this.currentSpec!);
            });

            // Implement
            await this.executePhase('coding', async () => {
                return this.coder.implement(task);
            });

            // Security scan
            await this.executePhase('security', async () => {
                const result = await this.security.scan([task.title]);
                if (result.threats.some(t => t.severity === 'critical')) {
                    this.escalate({
                        type: 'security_critical',
                        description: 'Critical security vulnerability detected',
                        context: result,
                        timestamp: new Date()
                    });
                }
                return result;
            });

            // Review
            const reviewResult = await this.executePhase('review', async () => {
                return this.reviewer.review(
                    { files: [], changes: 0 },
                    this.currentSpec!
                );
            });

            if (reviewResult.approved) {
                passed = true;
                this.log('success', 'Orchestrator', `Task "${task.title}" completed`);
            } else {
                // Fix issues
                this.fixerIterations++;
                await this.executePhase('fixing', async () => {
                    return this.fixer.fix(reviewResult.issues);
                });
            }
        }

        if (!passed) {
            this.escalate({
                type: 'fixer_loop',
                description: `Task "${task.title}" failed after ${this.config.maxFixIterations} iterations`,
                context: task,
                timestamp: new Date()
            });
        }
    }

    /**
     * Execute a pipeline phase
     */
    private async executePhase<T>(phase: PipelinePhase, fn: () => Promise<T>): Promise<T> {
        this.state.currentPhase = phase;
        this.state.currentAgent = phase;
        this.log('info', phase, `Starting ${phase} phase`);
        this.emit('phase', phase);

        const result = await fn();
        
        this.log('info', phase, `Completed ${phase} phase`);
        return result;
    }

    /**
     * Escalate to human
     */
    private escalate(event: EscalationEvent): void {
        this.state.status = 'escalated';
        this.log('warn', 'Orchestrator', `Escalating: ${event.description}`);
        this.emit('escalation', event);
    }

    /**
     * Pause execution
     */
    pause(): void {
        if (this.state.status === 'running') {
            this.state.status = 'paused';
            this.log('info', 'Orchestrator', 'Pipeline paused');
            this.emit('paused');
        }
    }

    /**
     * Resume execution
     */
    resume(): void {
        if (this.state.status === 'paused') {
            this.state.status = 'running';
            this.log('info', 'Orchestrator', 'Pipeline resumed');
            this.emit('resumed');
        }
    }

    /**
     * Stop execution
     */
    stop(): void {
        this.state.status = 'failed';
        this.stopCheckpointTimer();
        this.log('warn', 'Orchestrator', 'Pipeline stopped by user');
        this.emit('stopped');
    }

    /**
     * Get current state
     */
    getState(): PipelineState {
        return { ...this.state };
    }

    /**
     * Get logs
     */
    getLogs(limit = 50): LogEntry[] {
        return this.state.logs.slice(-limit);
    }

    // Private helpers

    private createInitialState(): PipelineState {
        return {
            status: 'idle',
            currentPhase: 'research',
            currentAgent: null,
            startTime: null,
            progress: 0,
            tasksCompleted: 0,
            tasksTotal: 0,
            currentTask: null,
            lastCheckpoint: null,
            logs: []
        };
    }

    private log(level: LogEntry['level'], agent: string, message: string): void {
        const entry: LogEntry = {
            timestamp: new Date(),
            agent,
            level,
            message
        };
        this.state.logs.push(entry);
        this.emit('log', entry);

        // Keep logs bounded
        if (this.state.logs.length > 1000) {
            this.state.logs = this.state.logs.slice(-500);
        }
    }

    private updateProgress(): void {
        if (this.state.tasksTotal > 0) {
            this.state.progress = Math.round(
                (this.state.tasksCompleted / this.state.tasksTotal) * 100
            );
        }
        this.emit('progress', this.state.progress);
    }

    private startCheckpointTimer(): void {
        this.checkpointTimer = setInterval(() => {
            this.checkpoint();
        }, this.config.checkpointInterval);
    }

    private stopCheckpointTimer(): void {
        if (this.checkpointTimer) {
            clearInterval(this.checkpointTimer);
            this.checkpointTimer = null;
        }
    }

    private async checkpoint(): Promise<void> {
        this.state.lastCheckpoint = new Date();
        this.log('info', 'Orchestrator', 'Checkpoint saved');
        this.emit('checkpoint', this.state);
        
        // TODO: Save state to RLM
        // await this.rlm.saveState(this.state);
    }
}
