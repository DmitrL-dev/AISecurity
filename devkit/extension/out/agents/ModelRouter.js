"use strict";
/**
 * ModelRouter
 * Routes agent types to appropriate Claude models based on task complexity
 *
 * Model Selection:
 * - haiku: Fast exploration, parallel recon (researcher)
 * - sonnet: Implementation tasks (coder, tester, fixer)
 * - opus: Critical thinking, security, architecture (security, reviewer)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ModelRouter = void 0;
class ModelRouter {
    constructor() {
        /**
         * Model matrix: agent type → default model
         * Based on Swarm Mode research patterns
         */
        this.modelMatrix = {
            'researcher': 'haiku', // Fast parallel exploration
            'planner': 'sonnet', // Task decomposition
            'tester': 'sonnet', // Test generation
            'coder': 'sonnet', // Implementation
            'security': 'opus', // Critical thinking, vulnerability analysis
            'reviewer': 'opus', // Deep code review
            'fixer': 'sonnet', // Bug fixes
            'integrator': 'sonnet' // Synthesis
        };
    }
    /**
     * Get the appropriate model for an agent type
     * High complexity tasks always use opus
     */
    getModel(agentType, taskComplexity) {
        // Override to opus for high complexity
        if (taskComplexity === 'high') {
            return 'opus';
        }
        return this.modelMatrix[agentType];
    }
    /**
     * Get model API identifier for Claude API
     */
    getModelId(model) {
        const modelIds = {
            'haiku': 'claude-3-haiku-20240307',
            'sonnet': 'claude-sonnet-4-20250514',
            'opus': 'claude-3-opus-20240229'
        };
        return modelIds[model];
    }
    /**
     * Check if agent type requires premium model
     */
    requiresPremiumModel(agentType) {
        return this.modelMatrix[agentType] === 'opus';
    }
}
exports.ModelRouter = ModelRouter;
//# sourceMappingURL=ModelRouter.js.map