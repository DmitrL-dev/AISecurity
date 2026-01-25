"use strict";
/**
 * Researcher Agent
 * Gathers project context using RLM Memory Bridge semantic search
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ResearcherAgent = void 0;
const AgentRegistry_1 = require("./AgentRegistry");
/**
 * Researcher Agent - Gathers context before planning/coding
 * Uses RLM Memory Bridge for semantic search across project knowledge
 */
class ResearcherAgent {
    constructor(rlmEndpoint = 'http://localhost:3000') {
        this.id = 'researcher';
        this.name = 'Researcher';
        this.role = AgentRegistry_1.AgentRole.PLANNER; // Works in planning phase
        this.status = AgentRegistry_1.AgentStatus.IDLE;
        this.rlmEndpoint = rlmEndpoint;
    }
    /**
     * Research a query using RLM semantic search
     */
    async research(query) {
        this.status = AgentRegistry_1.AgentStatus.RUNNING;
        try {
            // Call RLM route_context for semantic search
            const response = await this.callRLM('rlm_route_context', {
                query,
                max_tokens: 2000
            });
            const facts = this.parseFacts(response);
            const domains = [...new Set(facts.map(f => f.domain).filter(Boolean))];
            // Generate suggestions based on found context
            const suggestions = this.generateSuggestions(facts, query);
            this.status = AgentRegistry_1.AgentStatus.COMPLETED;
            this.lastRun = new Date();
            this.output = `Found ${facts.length} relevant facts across ${domains.length} domains`;
            return {
                query,
                facts,
                domains,
                suggestions,
                tokensSaved: response.tokens_saved || 0
            };
        }
        catch (error) {
            this.status = AgentRegistry_1.AgentStatus.FAILED;
            this.output = `Research failed: ${error}`;
            return {
                query,
                facts: [],
                domains: [],
                suggestions: [],
                tokensSaved: 0
            };
        }
    }
    /**
     * Gather full project context for planning
     */
    async gatherContext(topic) {
        this.status = AgentRegistry_1.AgentStatus.RUNNING;
        try {
            // Use RLM enterprise_context for comprehensive discovery
            const response = await this.callRLM('rlm_enterprise_context', {
                query: topic,
                mode: 'auto',
                include_causal: true,
                max_tokens: 3000
            });
            const context = {
                architecture: this.extractCategory(response, 'architecture'),
                conventions: this.extractCategory(response, 'conventions'),
                dependencies: this.extractCategory(response, 'dependencies'),
                recentDecisions: this.extractCategory(response, 'decisions')
            };
            this.status = AgentRegistry_1.AgentStatus.COMPLETED;
            this.lastRun = new Date();
            return context;
        }
        catch (error) {
            this.status = AgentRegistry_1.AgentStatus.FAILED;
            return {
                architecture: [],
                conventions: [],
                dependencies: [],
                recentDecisions: []
            };
        }
    }
    /**
     * Search for similar past decisions
     */
    async findSimilarDecisions(decision) {
        try {
            const response = await this.callRLM('rlm_get_causal_chain', {
                query: decision,
                max_depth: 5
            });
            return response.decisions?.map((d) => d.description) || [];
        }
        catch {
            return [];
        }
    }
    /**
     * Call RLM MCP tool
     */
    async callRLM(tool, params) {
        // In VS Code extension context, we'd use MCP client
        // For now, simulate the call structure
        try {
            const response = await fetch(`${this.rlmEndpoint}/mcp/${tool}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            return await response.json();
        }
        catch {
            // Fallback: return empty response
            return { facts: [], tokens_saved: 0 };
        }
    }
    /**
     * Parse facts from RLM response
     */
    parseFacts(response) {
        if (!response.facts)
            return [];
        return response.facts.map((f, index) => ({
            id: f.id || `fact-${index}`,
            content: f.content || f.text || '',
            level: this.parseLevel(f.level),
            domain: f.domain,
            relevance: f.score || f.relevance || 0.5
        }));
    }
    /**
     * Parse memory level
     */
    parseLevel(level) {
        if (typeof level === 'number') {
            return `L${level}`;
        }
        if (typeof level === 'string' && level.startsWith('L')) {
            return level;
        }
        return 'L2';
    }
    /**
     * Extract category from response
     */
    extractCategory(response, category) {
        if (response[category]) {
            return Array.isArray(response[category])
                ? response[category]
                : [response[category]];
        }
        return [];
    }
    /**
     * Generate suggestions based on found facts
     */
    generateSuggestions(facts, query) {
        const suggestions = [];
        // Suggest based on L0 core facts
        const coreFacts = facts.filter(f => f.level === 'L0');
        if (coreFacts.length > 0) {
            suggestions.push(`Consider core constraints: ${coreFacts.map(f => f.content).join(', ')}`);
        }
        // Suggest based on domain patterns
        const domains = [...new Set(facts.map(f => f.domain).filter(Boolean))];
        if (domains.length > 0) {
            suggestions.push(`Relevant domains: ${domains.join(', ')}`);
        }
        // Suggest if no facts found
        if (facts.length === 0) {
            suggestions.push(`No prior context found for "${query}". Consider documenting decisions.`);
        }
        return suggestions;
    }
}
exports.ResearcherAgent = ResearcherAgent;
//# sourceMappingURL=ResearcherAgent.js.map