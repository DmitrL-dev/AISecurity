/**
 * Researcher Agent
 * Gathers project context using RLM Memory Bridge semantic search
 */

import { BaseAgent, AgentRole, AgentStatus, Agent } from './AgentRegistry';

/**
 * Research result from context gathering
 */
export interface ResearchResult {
    query: string;
    facts: RelevantFact[];
    domains: string[];
    suggestions: string[];
    tokensSaved: number;
}

/**
 * Fact retrieved from RLM
 */
export interface RelevantFact {
    id: string;
    content: string;
    level: 'L0' | 'L1' | 'L2' | 'L3';
    domain?: string;
    relevance: number;
}

/**
 * Context for planning/coding
 */
export interface ProjectContext {
    architecture: string[];
    conventions: string[];
    dependencies: string[];
    recentDecisions: string[];
}

/**
 * Researcher Agent - Gathers context before planning/coding
 * Uses RLM Memory Bridge for semantic search across project knowledge
 */
export class ResearcherAgent implements Agent {
    id = 'researcher';
    name = 'Researcher';
    role = AgentRole.PLANNER; // Works in planning phase
    status: AgentStatus = AgentStatus.IDLE;
    lastRun?: Date;
    output?: string;

    private rlmEndpoint: string;

    constructor(rlmEndpoint: string = 'http://localhost:3000') {
        this.rlmEndpoint = rlmEndpoint;
    }

    /**
     * Research a query using RLM semantic search
     */
    async research(query: string): Promise<ResearchResult> {
        this.status = AgentStatus.RUNNING;

        try {
            // Call RLM route_context for semantic search
            const response = await this.callRLM('rlm_route_context', {
                query,
                max_tokens: 2000
            });

            const facts: RelevantFact[] = this.parseFacts(response);
            const domains = [...new Set(facts.map(f => f.domain).filter(Boolean))] as string[];

            // Generate suggestions based on found context
            const suggestions = this.generateSuggestions(facts, query);

            this.status = AgentStatus.COMPLETED;
            this.lastRun = new Date();
            this.output = `Found ${facts.length} relevant facts across ${domains.length} domains`;

            return {
                query,
                facts,
                domains,
                suggestions,
                tokensSaved: response.tokens_saved || 0
            };
        } catch (error) {
            this.status = AgentStatus.FAILED;
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
    async gatherContext(topic: string): Promise<ProjectContext> {
        this.status = AgentStatus.RUNNING;

        try {
            // Use RLM enterprise_context for comprehensive discovery
            const response = await this.callRLM('rlm_enterprise_context', {
                query: topic,
                mode: 'auto',
                include_causal: true,
                max_tokens: 3000
            });

            const context: ProjectContext = {
                architecture: this.extractCategory(response, 'architecture'),
                conventions: this.extractCategory(response, 'conventions'),
                dependencies: this.extractCategory(response, 'dependencies'),
                recentDecisions: this.extractCategory(response, 'decisions')
            };

            this.status = AgentStatus.COMPLETED;
            this.lastRun = new Date();

            return context;
        } catch (error) {
            this.status = AgentStatus.FAILED;
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
    async findSimilarDecisions(decision: string): Promise<string[]> {
        try {
            const response = await this.callRLM('rlm_get_causal_chain', {
                query: decision,
                max_depth: 5
            });

            return response.decisions?.map((d: any) => d.description) || [];
        } catch {
            return [];
        }
    }

    /**
     * Call RLM MCP tool
     */
    private async callRLM(tool: string, params: Record<string, any>): Promise<any> {
        // In VS Code extension context, we'd use MCP client
        // For now, simulate the call structure
        try {
            const response = await fetch(`${this.rlmEndpoint}/mcp/${tool}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            return await response.json();
        } catch {
            // Fallback: return empty response
            return { facts: [], tokens_saved: 0 };
        }
    }

    /**
     * Parse facts from RLM response
     */
    private parseFacts(response: any): RelevantFact[] {
        if (!response.facts) return [];

        return response.facts.map((f: any, index: number) => ({
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
    private parseLevel(level: any): 'L0' | 'L1' | 'L2' | 'L3' {
        if (typeof level === 'number') {
            return `L${level}` as 'L0' | 'L1' | 'L2' | 'L3';
        }
        if (typeof level === 'string' && level.startsWith('L')) {
            return level as 'L0' | 'L1' | 'L2' | 'L3';
        }
        return 'L2';
    }

    /**
     * Extract category from response
     */
    private extractCategory(response: any, category: string): string[] {
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
    private generateSuggestions(facts: RelevantFact[], query: string): string[] {
        const suggestions: string[] = [];

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
