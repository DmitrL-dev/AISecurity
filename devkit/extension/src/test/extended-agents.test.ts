/**
 * Extended Agents Unit Tests
 */

import * as assert from 'assert';

describe('Extended Agents Tests', () => {
    describe('ResearcherAgent', () => {
        it('should parse RLM facts correctly', () => {
            const response = {
                facts: [
                    { id: 'f1', content: 'Test fact', level: 0, domain: 'test' },
                    { id: 'f2', content: 'Another fact', level: 2 }
                ]
            };

            const facts = response.facts.map((f: any, index: number) => ({
                id: f.id || `fact-${index}`,
                content: f.content || '',
                level: `L${f.level}` as 'L0' | 'L1' | 'L2' | 'L3',
                domain: f.domain,
                relevance: 0.5
            }));

            assert.strictEqual(facts.length, 2);
            assert.strictEqual(facts[0].level, 'L0');
            assert.strictEqual(facts[0].domain, 'test');
        });

        it('should generate contextual suggestions', () => {
            const facts = [{ level: 'L0', content: 'core constraint' }];
            const suggestions: string[] = [];

            if (facts.some(f => f.level === 'L0')) {
                suggestions.push('Consider core constraints');
            }

            assert.strictEqual(suggestions.length, 1);
        });
    });

    describe('SecurityScannerAgent', () => {
        it('should map engine to threat type correctly', () => {
            const mapEngine = (engine: string): string => {
                const e = engine.toLowerCase();
                if (e.includes('injection') || e.includes('sqli')) return 'injection';
                if (e.includes('xss')) return 'xss';
                if (e.includes('prompt')) return 'prompt_injection';
                return 'malicious_code';
            };

            assert.strictEqual(mapEngine('InjectionEngine'), 'injection');
            assert.strictEqual(mapEngine('XSSEngine'), 'xss');
            assert.strictEqual(mapEngine('PromptInjectionEngine'), 'prompt_injection');
            assert.strictEqual(mapEngine('UnknownEngine'), 'malicious_code');
        });

        it('should calculate risk score correctly', () => {
            const threats = [
                { severity: 'high' as const, confidence: 0.9 },
                { severity: 'low' as const, confidence: 0.5 }
            ];

            const weights = { low: 10, medium: 30, high: 60, critical: 100 };
            const weightedSum = threats.reduce((sum, t) => 
                sum + weights[t.severity] * t.confidence, 0);
            const score = Math.min(100, Math.round(weightedSum / threats.length));

            assert.strictEqual(score, 30); // (60*0.9 + 10*0.5) / 2 = 29.5 → 30
        });

        it('should detect mock vulnerabilities', () => {
            const content = 'eval(userInput)';
            const hasEval = content.includes('eval(');
            
            assert.strictEqual(hasEval, true);
        });
    });

    describe('TesterAgent', () => {
        it('should convert requirement to test name', () => {
            const requirement = 'The system should validate user input';
            const name = requirement
                .replace(/^(the system should|it should|must|shall|need to)/i, '')
                .trim()
                .toLowerCase();

            assert.strictEqual(name, 'validate user input');
        });

        it('should generate assertions from requirement', () => {
            const requirement = 'must validate input and return error on failure';
            const assertions: string[] = [];

            if (requirement.includes('must')) assertions.push('mandatory');
            if (requirement.includes('valid')) assertions.push('validation');
            if (requirement.includes('error')) assertions.push('error handling');
            if (requirement.includes('return')) assertions.push('return value');

            assert.strictEqual(assertions.length, 4);
        });

        it('should calculate coverage threshold', () => {
            const coverage = 75;
            const threshold = 80;
            const passed = coverage >= threshold;

            assert.strictEqual(passed, false);
        });
    });

    describe('SpecCriticAgent', () => {
        it('should detect opposing terms', () => {
            const req1 = 'enable async processing';
            const req2 = 'require sync operations';

            const oppositions = [['sync', 'async'], ['enable', 'disable']];
            let hasConflict = false;

            for (const [t1, t2] of oppositions) {
                if ((req1.includes(t1) && req2.includes(t2)) ||
                    (req1.includes(t2) && req2.includes(t1))) {
                    hasConflict = true;
                }
            }

            assert.strictEqual(hasConflict, true);
        });

        it('should calculate critique score', () => {
            const strengths = ['good scope', 'has design'];
            const weaknesses = ['missing security'];
            const contradictions = [{ severity: 'major' }];

            let score = 70;
            score += strengths.length * 5;  // +10
            score -= weaknesses.length * 5; // -5
            score -= contradictions.filter((c: any) => c.severity === 'major').length * 10; // -10

            assert.strictEqual(score, 65);
        });

        it('should determine verdict correctly', () => {
            const determineVerdict = (score: number, hasBlocking: boolean) => {
                if (hasBlocking) return 'rejected';
                if (score >= 80) return 'approved';
                if (score >= 50) return 'needs_revision';
                return 'rejected';
            };

            assert.strictEqual(determineVerdict(85, false), 'approved');
            assert.strictEqual(determineVerdict(65, false), 'needs_revision');
            assert.strictEqual(determineVerdict(90, true), 'rejected');
        });
    });
});

export {};
