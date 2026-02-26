/**
 * SwarmSpawner
 * Manages parallel worker spawning with dependency resolution
 * 
 * Patterns:
 * - Fan-Out: Independent tasks in parallel
 * - Pipeline: Sequential with blockedBy dependencies
 * - Map-Reduce: Collect → Process → Merge
 */

import { ModelRouter, AgentType, ClaudeModel } from './ModelRouter';
import { WorkerPreamble } from './WorkerPreamble';

export interface SwarmTask {
    id: string;
    agentType: AgentType;
    description: string;
    blockedBy?: string[];
    context?: {
        codebase?: string;
        patterns?: string[];
        constraints?: string[];
    };
}

export interface AgentResult {
    taskId: string;
    success: boolean;
    output: string;
    error?: string;
    duration?: number;
}

export interface SwarmProgress {
    total: number;
    completed: number;
    pending: number;
    failed: number;
}

/**
 * Mock Claude API interface (replace with actual ClaudeAPIClient)
 */
interface ClaudeAPI {
    chat(prompt: string, options: { model: string }): Promise<string>;
}

export class SwarmSpawner {
    private modelRouter: ModelRouter;
    private results: Map<string, AgentResult> = new Map();

    constructor(
        private claude?: ClaudeAPI
    ) {
        this.modelRouter = new ModelRouter();
    }

    /**
     * Spawn parallel independent tasks (Fan-Out pattern)
     * All tasks with no blockers run simultaneously
     */
    async spawnParallel(tasks: SwarmTask[]): Promise<Map<string, AgentResult>> {
        const ready = tasks.filter(t => !t.blockedBy?.length);
        
        const promises = ready.map(task => this.spawnWorker(task));
        const results = await Promise.all(promises);
        
        const resultMap = new Map<string, AgentResult>();
        results.forEach((result, index) => {
            resultMap.set(ready[index].id, result);
            this.results.set(ready[index].id, result);
        });
        
        return resultMap;
    }

    /**
     * Spawn pipeline with dependency resolution
     * Tasks run when all their blockers are complete
     */
    async spawnPipeline(tasks: SwarmTask[]): Promise<Map<string, AgentResult>> {
        const pending = [...tasks];
        const allResults = new Map<string, AgentResult>();
        
        while (pending.length > 0) {
            // Find ready tasks (no pending blockers)
            const ready = pending.filter(task => 
                !task.blockedBy?.some(dep => !allResults.has(dep))
            );
            
            if (ready.length === 0 && pending.length > 0) {
                throw new Error('Circular dependency detected in task graph');
            }
            
            // Execute ready batch in parallel
            const batchResults = await this.spawnParallel(ready);
            
            // Collect results
            batchResults.forEach((result, taskId) => {
                allResults.set(taskId, result);
            });
            
            // Remove completed tasks from pending
            ready.forEach(task => {
                const index = pending.findIndex(t => t.id === task.id);
                if (index !== -1) pending.splice(index, 1);
            });
        }
        
        return allResults;
    }

    /**
     * Spawn a single worker agent
     */
    private async spawnWorker(task: SwarmTask): Promise<AgentResult> {
        const startTime = Date.now();
        const model = this.modelRouter.getModel(task.agentType);
        const modelId = this.modelRouter.getModelId(model);
        
        const prompt = task.context 
            ? WorkerPreamble.generateWithContext(task.description, task.context)
            : WorkerPreamble.generate(task.description);
        
        try {
            if (this.claude) {
                const output = await this.claude.chat(prompt, { model: modelId });
                return {
                    taskId: task.id,
                    success: true,
                    output,
                    duration: Date.now() - startTime
                };
            } else {
                // Mock response for testing
                return {
                    taskId: task.id,
                    success: true,
                    output: `[MOCK] Completed: ${task.description}`,
                    duration: Date.now() - startTime
                };
            }
        } catch (error) {
            return {
                taskId: task.id,
                success: false,
                output: '',
                error: error instanceof Error ? error.message : 'Unknown error',
                duration: Date.now() - startTime
            };
        }
    }

    /**
     * Get tasks that are ready to execute (no pending blockers)
     */
    getReadyTasks(tasks: SwarmTask[]): SwarmTask[] {
        return tasks.filter(task => 
            !task.blockedBy?.some(dep => !this.results.has(dep))
        );
    }

    /**
     * Get current progress
     */
    getProgress(tasks: SwarmTask[]): SwarmProgress {
        const completed = tasks.filter(t => this.results.has(t.id));
        const failed = completed.filter(t => !this.results.get(t.id)?.success);
        
        return {
            total: tasks.length,
            completed: completed.length,
            pending: tasks.length - completed.length,
            failed: failed.length
        };
    }

    /**
     * Estimate swarm size based on task description
     */
    static estimateSwarmSize(task: string): number {
        const lower = task.toLowerCase();
        
        if (lower.includes('security') || lower.includes('audit')) {
            return 10; // Security audit needs thorough coverage
        }
        if (lower.includes('feature') || lower.includes('implement')) {
            return 4; // Feature needs research + impl + test + review
        }
        if (lower.includes('fix') || lower.includes('bug')) {
            return 2; // Bug fix is usually focused
        }
        
        return 2; // Default minimum swarm
    }

    /**
     * Clear all results (reset for new run)
     */
    clearResults(): void {
        this.results.clear();
    }
}
