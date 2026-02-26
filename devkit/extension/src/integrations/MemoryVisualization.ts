/**
 * Memory Visualization
 * Visualizes RLM facts as graph
 */

/**
 * Fact node for visualization
 */
export interface FactNode {
    id: string;
    content: string;
    level: number;
    domain?: string;
    createdAt?: Date;
}

/**
 * Edge between facts
 */
export interface FactEdge {
    source: string;
    target: string;
    type?: string;
}

/**
 * Graph structure
 */
interface FactGraph {
    nodes: FactNode[];
    edges: FactEdge[];
}

/**
 * Memory Visualization service
 */
export class MemoryVisualization {
    private facts: Map<string, FactNode> = new Map();
    private edges: FactEdge[] = [];

    /**
     * Load facts from RLM (mock)
     */
    async loadFacts(): Promise<FactNode[]> {
        // In real implementation, this would call RLM MCP tools
        return Array.from(this.facts.values());
    }

    /**
     * Add fact to graph
     */
    addFact(fact: FactNode): void {
        this.facts.set(fact.id, {
            ...fact,
            createdAt: fact.createdAt || new Date()
        });
    }

    /**
     * Add edge between facts
     */
    addEdge(sourceId: string, targetId: string, type?: string): void {
        this.edges.push({ source: sourceId, target: targetId, type });
    }

    /**
     * Get full graph
     */
    getGraph(): FactGraph {
        return {
            nodes: Array.from(this.facts.values()),
            edges: [...this.edges]
        };
    }

    /**
     * Get facts by level
     */
    getFactsByLevel(level: number): FactNode[] {
        return Array.from(this.facts.values()).filter(f => f.level === level);
    }

    /**
     * Get facts by domain
     */
    getFactsByDomain(domain: string): FactNode[] {
        return Array.from(this.facts.values()).filter(f => f.domain === domain);
    }

    /**
     * Search facts by content (simple keyword match)
     */
    async searchFacts(query: string): Promise<FactNode[]> {
        const queryLower = query.toLowerCase();
        const keywords = ['test', 'tdd', 'testing']; // Expand for semantic
        
        return Array.from(this.facts.values()).filter(f => {
            const contentLower = f.content.toLowerCase();
            
            // Direct match
            if (contentLower.includes(queryLower)) return true;
            
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
    toDOT(): string {
        const lines: string[] = ['digraph MemoryGraph {'];
        lines.push('  rankdir=TB;');
        lines.push('  node [shape=box, style=rounded];');
        lines.push('');

        // Level colors
        const levelColors: Record<number, string> = {
            0: '#ef4444', // Red - Core
            1: '#3b82f6', // Blue - Session
            2: '#10b981'  // Green - Project
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
    getStats(): { total: number; byLevel: Record<number, number>; edges: number } {
        const byLevel: Record<number, number> = {};
        
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
    clear(): void {
        this.facts.clear();
        this.edges = [];
    }
}
