"use strict";
/**
 * Agent Orchestrator
 * Manages autonomous pipeline execution for 24/7 operation
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentOrchestrator = void 0;
const events_1 = require("events");
const AgentRegistry_1 = require("./AgentRegistry");
const ResearcherAgent_1 = require("./ResearcherAgent");
const SecurityScannerAgent_1 = require("./SecurityScannerAgent");
const TesterAgent_1 = require("./TesterAgent");
const SpecCriticAgent_1 = require("./SpecCriticAgent");
/**
 * Agent Orchestrator - Manages autonomous pipeline
 */
class AgentOrchestrator extends events_1.EventEmitter {
    constructor(config = {}) {
        super();
        // State
        this.currentSpec = null;
        this.currentPlan = null;
        this.fixerIterations = 0;
        this.checkpointTimer = null;
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
        this.registry = new AgentRegistry_1.AgentRegistry();
        // Initialize agents
        this.researcher = new ResearcherAgent_1.ResearcherAgent(this.config.endpoints.rlm);
        this.planner = new AgentRegistry_1.PlannerAgent();
        this.critic = new SpecCriticAgent_1.SpecCriticAgent(this.config.endpoints.rlm);
        this.tester = new TesterAgent_1.TesterAgent();
        this.coder = new AgentRegistry_1.CoderAgent();
        this.security = new SecurityScannerAgent_1.SecurityScannerAgent(this.config.endpoints.brain, this.config.endpoints.brainApiKey);
        this.reviewer = new AgentRegistry_1.ReviewerAgent();
        this.fixer = new AgentRegistry_1.FixerAgent();
    }
    /**
     * Start autonomous execution of a global task
     */
    async execute(task) {
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
            const spec = { title: task, requirements: [task] };
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
            for (const task of this.currentPlan.tasks) {
                await this.executeTask(task);
                this.state.tasksCompleted++;
                this.updateProgress();
            }
            this.state.status = 'completed';
            this.state.currentPhase = 'completed';
            this.log('success', 'Orchestrator', 'Pipeline completed successfully');
        }
        catch (error) {
            this.state.status = 'failed';
            this.log('error', 'Orchestrator', `Pipeline failed: ${error.message}`);
            this.emit('error', error);
        }
        finally {
            this.stopCheckpointTimer();
        }
        return this.state;
    }
    /**
     * Execute a single task through the pipeline
     */
    async executeTask(task) {
        this.state.currentTask = task.title;
        this.fixerIterations = 0;
        let passed = false;
        while (!passed && this.fixerIterations < this.config.maxFixIterations) {
            // Generate tests
            await this.executePhase('testing', async () => {
                return this.tester.generateTests(this.currentSpec);
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
                return this.reviewer.review({ files: [], changes: 0 }, this.currentSpec);
            });
            if (reviewResult.approved) {
                passed = true;
                this.log('success', 'Orchestrator', `Task "${task.title}" completed`);
            }
            else {
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
    async executePhase(phase, fn) {
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
    escalate(event) {
        this.state.status = 'escalated';
        this.log('warn', 'Orchestrator', `Escalating: ${event.description}`);
        this.emit('escalation', event);
    }
    /**
     * Pause execution
     */
    pause() {
        if (this.state.status === 'running') {
            this.state.status = 'paused';
            this.log('info', 'Orchestrator', 'Pipeline paused');
            this.emit('paused');
        }
    }
    /**
     * Resume execution
     */
    resume() {
        if (this.state.status === 'paused') {
            this.state.status = 'running';
            this.log('info', 'Orchestrator', 'Pipeline resumed');
            this.emit('resumed');
        }
    }
    /**
     * Stop execution
     */
    stop() {
        this.state.status = 'failed';
        this.stopCheckpointTimer();
        this.log('warn', 'Orchestrator', 'Pipeline stopped by user');
        this.emit('stopped');
    }
    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }
    /**
     * Get logs
     */
    getLogs(limit = 50) {
        return this.state.logs.slice(-limit);
    }
    // Private helpers
    createInitialState() {
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
    log(level, agent, message) {
        const entry = {
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
    updateProgress() {
        if (this.state.tasksTotal > 0) {
            this.state.progress = Math.round((this.state.tasksCompleted / this.state.tasksTotal) * 100);
        }
        this.emit('progress', this.state.progress);
    }
    startCheckpointTimer() {
        this.checkpointTimer = setInterval(() => {
            this.checkpoint();
        }, this.config.checkpointInterval);
    }
    stopCheckpointTimer() {
        if (this.checkpointTimer) {
            clearInterval(this.checkpointTimer);
            this.checkpointTimer = null;
        }
    }
    async checkpoint() {
        this.state.lastCheckpoint = new Date();
        this.log('info', 'Orchestrator', 'Checkpoint saved');
        this.emit('checkpoint', this.state);
        // TODO: Save state to RLM
        // await this.rlm.saveState(this.state);
    }
}
exports.AgentOrchestrator = AgentOrchestrator;
//# sourceMappingURL=AgentOrchestrator.js.map