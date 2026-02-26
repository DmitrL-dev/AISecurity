"use strict";
/**
 * Memory Visualization
 * Visualizes RLM facts as graph
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryVisualization = void 0;
/**
 * Memory Visualization service
 */
class MemoryVisualization {
    constructor() {
        this.facts = new Map();
        this.edges = [];
    }
    /**
     * Load facts from RLM (mock)
     */
    async loadFacts() {
        // In real implementation, this would call RLM MCP tools
        return Array.from(this.facts.values());
    }
    /**
     * Add fact to graph
     */
    addFact(fact) {
        this.facts.set(fact.id, {
            ...fact,
            createdAt: fact.createdAt || new Date()
        });
    }
    /**
     * Add edge between facts
     */
    addEdge(sourceId, targetId, type) {
        this.edges.push({ source: sourceId, target: targetId, type });
    }
    /**
     * Get full graph
     */
    getGraph() {
        return {
            nodes: Array.from(this.facts.values()),
            edges: [...this.edges]
        };
    }
    /**
     * Get facts by level
     */
    getFactsByLevel(level) {
        return Array.from(this.facts.values()).filter(f => f.level === level);
    }
    /**
     * Get facts by domain
     */
    getFactsByDomain(domain) {
        return Array.from(this.facts.values()).filter(f => f.domain === domain);
    }
    /**
     * Search facts by content (simple keyword match)
     */
    async searchFacts(query) {
        const queryLower = query.toLowerCase();
        const keywords = ['test', 'tdd', 'testing']; // Expand for semantic
        return Array.from(this.facts.values()).filter(f => {
            const contentLower = f.content.toLowerCase();
            // Direct match
            if (contentLower.includes(queryLower))
                return true;
            // Semantic expansion for common terms
            if (queryLower === 'testing' || queryLower === 'test') {
                return keywords.some(k => contentLower.includes(k));
            }
            return false;
        });
    }
    /**
     * Export to DOT format for GraphViz
     */
    toDOT() {
        const lines = ['digraph MemoryGraph {'];
        lines.push('  rankdir=TB;');
        lines.push('  node [shape=box, style=rounded];');
        lines.push('');
        // Level colors
        const levelColors = {
            0: '#ef4444', // Red - Core
            1: '#3b82f6', // Blue - Session
            2: '#10b981' // Green - Project
        };
        // Add nodes
        for (const fact of this.facts.values()) {
            const color = levelColors[fact.level] || '#8b5cf6';
            const label = fact.content.replace(/"/g, '\\"').slice(0, 30);
            lines.push(`  "${fact.id}" [label="${label}", fillcolor="${color}", style="filled,rounded"];`);
        }
        lines.push('');
        // Add edges
        for (const edge of this.edges) {
            const style = edge.type === 'parent' ? 'solid' : 'dashed';
            lines.push(`  "${edge.source}" -> "${edge.target}" [style=${style}];`);
        }
        lines.push('}');
        return lines.join('\n');
    }
    /**
     * Get statistics
     */
    getStats() {
        const byLevel = {};
        for (const fact of this.facts.values()) {
            byLevel[fact.level] = (byLevel[fact.level] || 0) + 1;
        }
        return {
            total: this.facts.size,
            byLevel,
            edges: this.edges.length
        };
    }
    /**
     * Clear all data
     */
    clear() {
        this.facts.clear();
        this.edges = [];
    }
}
exports.MemoryVisualization = MemoryVisualization;
//# sourceMappingURL=MemoryVisualization.js.map