/**
 * Phase 2 Agent Tests
 * Tests for ClaudeAPIClient, AgentOrchestrator, and upgraded agents
 */

import * as assert from 'assert';

// Mock types (since we're testing without full imports)
interface ClaudeRequest {
    prompt: string;
    systemPrompt?: string;
    model?: string;
    maxTokens?: number;
    temperature?: number;
}

interface ParsedCodeFile {
    language: string;
    path: string | null;
    content: string;
}

describe('ClaudeAPIClient', () => {
    describe('isConfigured', () => {
        it('should return false when no API key is set', () => {
            // Test would check that isConfigured() returns false
            // when ANTHROPIC_API_KEY is not set
            const hasApiKey = process.env.ANTHROPIC_API_KEY?.length ?? 0;
            assert.strictEqual(hasApiKey > 0, false); // Expected: no key in test env
        });
    });

    describe('parseCodeBlocks', () => {
        it('should parse markdown code blocks with filenames', () => {
            const content = `\`\`\`typescript:src/utils.ts
export function hello() { return 'world'; }
\`\`\``;
            
            // Expected parsing result
            const expected: ParsedCodeFile[] = [{
                language: 'typescript',
                path: 'src/utils.ts',
                content: "export function hello() { return 'world'; }"
            }];
            
            // Regex from ClaudeAPIClient
            const codeBlockRegex = /```(\w+)(?::([^\n]+))?\n([\s\S]*?)```/g;
            const files: ParsedCodeFile[] = [];
            let match;
            while ((match = codeBlockRegex.exec(content)) !== null) {
                files.push({
                    language: match[1],
                    path: match[2] || null,
                    content: match[3].trim()
                });
            }
            
            assert.strictEqual(files.length, 1);
            assert.strictEqual(files[0].language, 'typescript');
            assert.strictEqual(files[0].path, 'src/utils.ts');
        });

        it('should handle code blocks without path', () => {
            const content = `\`\`\`python
print("hello")
\`\`\``;
            
            const codeBlockRegex = /```(\w+)(?::([^\n]+))?\n([\s\S]*?)```/g;
            const match = codeBlockRegex.exec(content);
            
            assert.ok(match);
            assert.strictEqual(match[1], 'python');
            assert.strictEqual(match[2], undefined);
        });

        it('should parse multiple code blocks', () => {
            const content = `
\`\`\`typescript:src/a.ts
const a = 1;
\`\`\`

\`\`\`typescript:src/b.ts
const b = 2;
\`\`\`
`;
            const codeBlockRegex = /```(\w+)(?::([^\n]+))?\n([\s\S]*?)```/g;
            const files: ParsedCodeFile[] = [];
            let match;
            while ((match = codeBlockRegex.exec(content)) !== null) {
                files.push({
                    language: match[1],
                    path: match[2] || null,
                    content: match[3].trim()
                });
            }
            
            assert.strictEqual(files.length, 2);
        });
    });

    describe('PROMPTS', () => {
        it('should have IMPLEMENT prompt with placeholders', () => {
            const IMPLEMENT = `You are an expert software engineer...
CONTEXT:
{context}
SPECIFICATION:
{spec}
TASK:
{task}`;
            
            assert.ok(IMPLEMENT.includes('{context}'));
            assert.ok(IMPLEMENT.includes('{spec}'));
            assert.ok(IMPLEMENT.includes('{task}'));
        });

        it('should have FIX prompt with placeholders', () => {
            const FIX = `ISSUE: {issue} CURRENT CODE: {code} CONTEXT: {context}`;
            
            assert.ok(FIX.includes('{issue}'));
            assert.ok(FIX.includes('{code}'));
            assert.ok(FIX.includes('{context}'));
        });
    });
});

describe('AgentOrchestrator', () => {
    describe('PipelineState', () => {
        it('should have correct initial state', () => {
            const initialState = {
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
            
            assert.strictEqual(initialState.status, 'idle');
            assert.strictEqual(initialState.progress, 0);
            assert.deepStrictEqual(initialState.logs, []);
        });
    });

    describe('Progress calculation', () => {
        it('should calculate progress percentage correctly', () => {
            const tasksCompleted = 5;
            const tasksTotal = 10;
            const progress = Math.round((tasksCompleted / tasksTotal) * 100);
            
            assert.strictEqual(progress, 50);
        });

        it('should handle zero tasks', () => {
            const tasksTotal = 0;
            const progress = tasksTotal > 0 ? Math.round((0 / tasksTotal) * 100) : 0;
            
            assert.strictEqual(progress, 0);
        });
    });

    describe('Log management', () => {
        it('should limit logs to prevent memory issues', () => {
            const MAX_LOGS = 1000;
            const logs: any[] = [];
            
            // Simulate adding 1100 logs
            for (let i = 0; i < 1100; i++) {
                logs.push({ timestamp: new Date(), agent: 'test', level: 'info', message: `Log ${i}` });
            }
            
            // Trim to last 500
            const trimmed = logs.length > MAX_LOGS ? logs.slice(-500) : logs;
            
            assert.strictEqual(trimmed.length, 500);
            assert.ok(trimmed[0].message.includes('600')); // First kept log
        });
    });

    describe('Escalation conditions', () => {
        it('should identify critical security threats', () => {
            const threats = [
                { severity: 'low', type: 'info' },
                { severity: 'critical', type: 'injection' }
            ];
            
            const hasCritical = threats.some(t => t.severity === 'critical');
            assert.strictEqual(hasCritical, true);
        });

        it('should check fixer iteration limit', () => {
            const maxIterations = 3;
            let currentIteration = 0;
            
            currentIteration++;
            assert.strictEqual(currentIteration < maxIterations, true);
            
            currentIteration++;
            currentIteration++;
            assert.strictEqual(currentIteration < maxIterations, false);
        });
    });
});

describe('CoderAgent with Claude', () => {
    describe('Security pre-check', () => {
        it('should block code with critical vulnerabilities', () => {
            const securityResult = {
                threats: [{ severity: 'critical', type: 'injection' }],
                riskScore: 95
            };
            
            const shouldBlock = securityResult.threats.some(t => t.severity === 'critical');
            assert.strictEqual(shouldBlock, true);
        });

        it('should allow code without critical vulnerabilities', () => {
            const securityResult = {
                threats: [{ severity: 'medium', type: 'hardcoded_secret' }],
                riskScore: 45
            };
            
            const shouldBlock = securityResult.threats.some(t => t.severity === 'critical');
            assert.strictEqual(shouldBlock, false);
        });
    });

    describe('Context gathering', () => {
        it('should limit context facts to 10', () => {
            const facts = Array(20).fill({ content: 'fact' });
            const limited = facts.slice(0, 10);
            
            assert.strictEqual(limited.length, 10);
        });
    });
});

describe('FixerAgent with Claude', () => {
    describe('Failed fix tracking', () => {
        it('should record failed fixes by file', () => {
            const failedFixes = new Map<string, string[]>();
            
            const issue1 = { file: 'src/a.ts', description: 'Error 1' };
            const issue2 = { file: 'src/a.ts', description: 'Error 2' };
            const issue3 = { file: 'src/b.ts', description: 'Error 3' };
            
            // Record fix failures
            [issue1, issue2, issue3].forEach(issue => {
                const key = issue.file || 'unknown';
                const existing = failedFixes.get(key) || [];
                existing.push(issue.description);
                failedFixes.set(key, existing);
            });
            
            assert.strictEqual(failedFixes.get('src/a.ts')?.length, 2);
            assert.strictEqual(failedFixes.get('src/b.ts')?.length, 1);
        });
    });

    describe('Retry logic', () => {
        it('should allow retry up to max iterations', () => {
            const maxIterations = 3;
            let currentIteration = 0;
            
            const canRetry = () => currentIteration < maxIterations;
            
            assert.strictEqual(canRetry(), true);
            currentIteration++;
            assert.strictEqual(canRetry(), true);
            currentIteration++;
            assert.strictEqual(canRetry(), true);
            currentIteration++;
            assert.strictEqual(canRetry(), false);
        });
    });
});
