/**
 * Spec Critic Agent
 * Self-critique using RLM causal chains
 * "Ultrathink" mode for deep analysis
 */

import { Agent, AgentRole, AgentStatus, Spec } from './AgentRegistry';

/**
 * Critique result
 */
export interface CritiqueResult {
    specId: string;
    score: number;           // 0-100
    verdict: 'approved' | 'needs_revision' | 'rejected';
    strengths: string[];
    weaknesses: string[];
    contradictions: Contradiction[];
    suggestions: CritiqueSuggestion[];
    causalAnalysis?: CausalAnalysis;
}

/**
 * Identified contradiction in spec
 */
export interface Contradiction {
    id: string;
    description: string;
    requirement1: string;
    requirement2: string;
    severity: 'minor' | 'major' | 'blocking';
}

/**
 * Improvement suggestion
 */
export interface CritiqueSuggestion {
    id: string;
    category: 'clarity' | 'completeness' | 'feasibility' | 'consistency' | 'security';
    description: string;
    priority: 'low' | 'medium' | 'high';
    affectedRequirements?: string[];
}

/**
 * Causal chain analysis from RLM
 */
export interface CausalAnalysis {
    relatedDecisions: string[];
    potentialConflicts: string[];
    historicalPatterns: string[];
    riskFactors: string[];
}

/**
 * Spec Critic Agent - Self-critique using "Ultrathink" methodology
 * 
 * Uses RLM causal chains to:
 * 1. Find contradictions in requirements
 * 2. Check against historical decisions
 * 3. Identify potential risks
 * 4. Suggest improvements
 */
export class SpecCriticAgent implements Agent {
    id = 'spec-critic';
    name = 'Spec Critic';
    role = AgentRole.REVIEWER;
    status: AgentStatus = AgentStatus.IDLE;
    lastRun?: Date;
    output?: string;

    private rlmEndpoint: string;

    constructor(rlmEndpoint: string = 'http://localhost:3000') {
        this.rlmEndpoint = rlmEndpoint;
    }

    /**
     * Perform deep critique of specification
     * "Ultrathink" mode - exhaustive analysis
     */
    async critique(spec: Spec): Promise<CritiqueResult> {
        this.status = AgentStatus.RUNNING;
        const specId = `spec-${Date.now()}`;

        try {
            // Phase 1: Internal consistency check
            const contradictions = this.findContradictions(spec);

            // Phase 2: Completeness analysis
            const completenessIssues = this.analyzeCompleteness(spec);

            // Phase 3: Historical context from RLM
            const causalAnalysis = await this.performCausalAnalysis(spec);

            // Phase 4: Generate strengths and weaknesses
            const { strengths, weaknesses } = this.evaluateSpec(spec, contradictions, completenessIssues);

            // Phase 5: Generate suggestions
            const suggestions = this.generateSuggestions(
                spec, 
                contradictions, 
                completenessIssues, 
                causalAnalysis
            );

            // Calculate score
            const score = this.calculateScore(strengths, weaknesses, contradictions);
            const verdict = this.determineVerdict(score, contradictions);

            this.status = AgentStatus.COMPLETED;
            this.lastRun = new Date();
            this.output = `Critique complete: score ${score}/100, verdict: ${verdict}`;

            return {
                specId,
                score,
                verdict,
                strengths,
                weaknesses,
                contradictions,
                suggestions,
                causalAnalysis
            };
        } catch (error) {
            this.status = AgentStatus.FAILED;
            this.output = `Critique failed: ${error}`;
            throw error;
        }
    }

    /**
     * Quick consistency check (no RLM)
     */
    async quickCheck(spec: Spec): Promise<{
        consistent: boolean;
        issues: string[];
    }> {
        const contradictions = this.findContradictions(spec);
        
        return {
            consistent: contradictions.length === 0,
            issues: contradictions.map(c => c.description)
        };
    }

    /**
     * Find contradictions between requirements
     */
    private findContradictions(spec: Spec): Contradiction[] {
        const contradictions: Contradiction[] = [];

        // Check each pair of requirements
        for (let i = 0; i < spec.requirements.length; i++) {
            for (let j = i + 1; j < spec.requirements.length; j++) {
                const req1 = spec.requirements[i];
                const req2 = spec.requirements[j];

                // Check for opposing terms
                if (this.hasOpposingTerms(req1, req2)) {
                    contradictions.push({
                        id: `contradiction-${i}-${j}`,
                        description: `Potential conflict between requirements`,
                        requirement1: req1,
                        requirement2: req2,
                        severity: 'major'
                    });
                }

                // Check for resource conflicts
                if (this.hasResourceConflict(req1, req2)) {
                    contradictions.push({
                        id: `resource-conflict-${i}-${j}`,
                        description: `Resource allocation conflict`,
                        requirement1: req1,
                        requirement2: req2,
                        severity: 'minor'
                    });
                }
            }
        }

        return contradictions;
    }

    /**
     * Check for opposing terms
     */
    private hasOpposingTerms(req1: string, req2: string): boolean {
        const oppositions = [
            ['sync', 'async'],
            ['block', 'allow'],
            ['enable', 'disable'],
            ['require', 'optional'],
            ['public', 'private'],
            ['fast', 'thorough'],
            ['simple', 'comprehensive']
        ];

        const r1Lower = req1.toLowerCase();
        const r2Lower = req2.toLowerCase();

        for (const [term1, term2] of oppositions) {
            if ((r1Lower.includes(term1) && r2Lower.includes(term2)) ||
                (r1Lower.includes(term2) && r2Lower.includes(term1))) {
                return true;
            }
        }

        return false;
    }

    /**
     * Check for resource conflicts
     */
    private hasResourceConflict(req1: string, req2: string): boolean {
        const resourceKeywords = ['memory', 'cpu', 'disk', 'network', 'database', 'cache'];
        const conflictKeywords = ['minimize', 'maximize', 'reduce', 'increase', 'limit', 'unlimited'];

        const r1Lower = req1.toLowerCase();
        const r2Lower = req2.toLowerCase();

        for (const resource of resourceKeywords) {
            if (r1Lower.includes(resource) && r2Lower.includes(resource)) {
                for (const conflict of conflictKeywords) {
                    if (r1Lower.includes(conflict) || r2Lower.includes(conflict)) {
                        return true;
                    }
                }
            }
        }

        return false;
    }

    /**
     * Analyze completeness of specification
     */
    private analyzeCompleteness(spec: Spec): string[] {
        const issues: string[] = [];

        // Check for missing common elements
        const mustHave = ['error handling', 'validation', 'security', 'performance'];
        const reqsLower = spec.requirements.map(r => r.toLowerCase()).join(' ');

        for (const element of mustHave) {
            if (!reqsLower.includes(element.split(' ')[0])) {
                issues.push(`Consider adding ${element} requirements`);
            }
        }

        // Check for vague requirements
        const vagueTerms = ['should be good', 'must be fast', 'needs to work', 'as needed'];
        for (const req of spec.requirements) {
            for (const vague of vagueTerms) {
                if (req.toLowerCase().includes(vague)) {
                    issues.push(`Vague requirement: "${req}" - needs measurable criteria`);
                }
            }
        }

        // Check minimum requirement count
        if (spec.requirements.length < 3) {
            issues.push('Specification may be incomplete - only has ' + spec.requirements.length + ' requirements');
        }

        return issues;
    }

    /**
     * Perform causal analysis using RLM
     */
    private async performCausalAnalysis(spec: Spec): Promise<CausalAnalysis> {
        try {
            // Query RLM for related decisions
            const response = await fetch(`${this.rlmEndpoint}/mcp/rlm_get_causal_chain`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: spec.title,
                    max_depth: 5
                })
            });

            const data = await response.json() as {
                decisions?: { description: string }[];
                conflicts?: string[];
                patterns?: string[];
                risks?: string[];
            };

            return {
                relatedDecisions: data.decisions?.map((d) => d.description) || [],
                potentialConflicts: data.conflicts || [],
                historicalPatterns: data.patterns || [],
                riskFactors: data.risks || []
            };
        } catch {
            // Return empty analysis if RLM unavailable
            return {
                relatedDecisions: [],
                potentialConflicts: [],
                historicalPatterns: [],
                riskFactors: []
            };
        }
    }

    /**
     * Evaluate spec strengths and weaknesses
     */
    private evaluateSpec(
        spec: Spec, 
        contradictions: Contradiction[], 
        completenessIssues: string[]
    ): { strengths: string[]; weaknesses: string[] } {
        const strengths: string[] = [];
        const weaknesses: string[] = [];

        // Positive: has design
        if (spec.design) {
            strengths.push('Includes design documentation');
        } else {
            weaknesses.push('Missing design documentation');
        }

        // Positive: good requirement count
        if (spec.requirements.length >= 5 && spec.requirements.length <= 15) {
            strengths.push('Appropriate scope (5-15 requirements)');
        }

        // Negative: contradictions
        if (contradictions.length > 0) {
            weaknesses.push(`Contains ${contradictions.length} potential contradictions`);
        } else {
            strengths.push('No internal contradictions detected');
        }

        // Negative: completeness
        if (completenessIssues.length > 0) {
            weaknesses.push(`${completenessIssues.length} completeness concerns`);
        } else {
            strengths.push('Covers standard requirement categories');
        }

        // Check for measurable requirements
        const measurable = spec.requirements.filter(r => 
            /\d+/.test(r) || r.includes('%') || r.includes('ms') || r.includes('seconds')
        );
        if (measurable.length > 0) {
            strengths.push(`${measurable.length} measurable requirements`);
        } else {
            weaknesses.push('No measurable/quantifiable requirements');
        }

        return { strengths, weaknesses };
    }

    /**
     * Generate improvement suggestions
     */
    private generateSuggestions(
        spec: Spec,
        contradictions: Contradiction[],
        completenessIssues: string[],
        causalAnalysis: CausalAnalysis
    ): CritiqueSuggestion[] {
        const suggestions: CritiqueSuggestion[] = [];

        // Suggestions from contradictions
        contradictions.forEach((c, i) => {
            suggestions.push({
                id: `suggest-contradiction-${i}`,
                category: 'consistency',
                description: `Resolve conflict: ${c.description}`,
                priority: c.severity === 'blocking' ? 'high' : 'medium',
                affectedRequirements: [c.requirement1, c.requirement2]
            });
        });

        // Suggestions from completeness
        completenessIssues.forEach((issue, i) => {
            suggestions.push({
                id: `suggest-completeness-${i}`,
                category: 'completeness',
                description: issue,
                priority: issue.includes('vague') ? 'high' : 'medium'
            });
        });

        // Suggestions from causal analysis
        if (causalAnalysis.potentialConflicts.length > 0) {
            suggestions.push({
                id: 'suggest-historical',
                category: 'consistency',
                description: 'Review historical decisions that may conflict',
                priority: 'high'
            });
        }

        // Always suggest security review
        if (!spec.requirements.some(r => r.toLowerCase().includes('security'))) {
            suggestions.push({
                id: 'suggest-security',
                category: 'security',
                description: 'Add explicit security requirements',
                priority: 'high'
            });
        }

        return suggestions;
    }

    /**
     * Calculate overall score
     */
    private calculateScore(
        strengths: string[], 
        weaknesses: string[], 
        contradictions: Contradiction[]
    ): number {
        let score = 70; // Base score

        // Add for strengths
        score += strengths.length * 5;

        // Subtract for weaknesses
        score -= weaknesses.length * 5;

        // Heavy penalty for contradictions
        const blockingCount = contradictions.filter(c => c.severity === 'blocking').length;
        const majorCount = contradictions.filter(c => c.severity === 'major').length;
        score -= blockingCount * 20;
        score -= majorCount * 10;

        // Clamp to 0-100
        return Math.max(0, Math.min(100, score));
    }

    /**
     * Determine verdict based on score and issues
     */
    private determineVerdict(
        score: number, 
        contradictions: Contradiction[]
    ): 'approved' | 'needs_revision' | 'rejected' {
        const hasBlocking = contradictions.some(c => c.severity === 'blocking');

        if (hasBlocking) return 'rejected';
        if (score >= 80) return 'approved';
        if (score >= 50) return 'needs_revision';
        return 'rejected';
    }
}
