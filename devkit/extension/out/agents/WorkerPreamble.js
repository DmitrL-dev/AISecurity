"use strict";
/**
 * WorkerPreamble
 * Generates standard preamble for spawned worker agents
 *
 * Iron Law: Workers execute, they do NOT orchestrate
 * - No sub-agent spawning
 * - No task management
 * - Direct tool usage only
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.WorkerPreamble = void 0;
class WorkerPreamble {
    /**
     * Generate standard worker preamble with task description
     * All spawned workers receive this context
     */
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
    /**
     * Generate preamble with additional context
     */
    static generateWithContext(taskDescription, context) {
        let preamble = this.generate(taskDescription);
        if (context.codebase) {
            preamble += `\n\nCODEBASE CONTEXT:\n${context.codebase}`;
        }
        if (context.patterns?.length) {
            preamble += `\n\nFOLLOW THESE PATTERNS:\n${context.patterns.map(p => `- ${p}`).join('\n')}`;
        }
        if (context.constraints?.length) {
            preamble += `\n\nCONSTRAINTS:\n${context.constraints.map(c => `- ${c}`).join('\n')}`;
        }
        return preamble;
    }
    /**
     * Generate minimal preamble for simple tasks
     */
    static generateMinimal(taskDescription) {
        return `WORKER AGENT. Task: ${taskDescription}. Use tools directly. No sub-agents.`;
    }
}
exports.WorkerPreamble = WorkerPreamble;
//# sourceMappingURL=WorkerPreamble.js.map