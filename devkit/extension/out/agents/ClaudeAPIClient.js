"use strict";
/**
 * Claude API Client
 * Wrapper for Anthropic Claude API for code generation and fixes
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ClaudeAPIClient = exports.PROMPTS = exports.SWARM_MODEL_MAP = void 0;
exports.getClaudeClient = getClaudeClient;
exports.SWARM_MODEL_MAP = {
    'haiku': 'claude-3-haiku-20240307',
    'sonnet': 'claude-sonnet-4-20250514',
    'opus': 'claude-3-opus-20240229'
};
/**
 * Code generation prompt templates
 */
exports.PROMPTS = {
    IMPLEMENT: `You are an expert software engineer working on the SENTINEL security platform.
Your task is to implement code based on the specification provided.

RULES:
1. Write clean, production-ready TypeScript/Python code
2. Include proper error handling
3. Add JSDoc/docstring comments for public APIs
4. Follow existing code patterns in the project
5. Security-first: never introduce vulnerabilities

CONTEXT:
{context}

SPECIFICATION:
{spec}

TASK:
{task}

Respond with ONLY the code, no explanations. Use markdown code blocks with filenames:

\`\`\`typescript:src/path/to/file.ts
// code here
\`\`\``,
    FIX: `You are an expert debugger working on fixing issues in the SENTINEL codebase.

ISSUE:
{issue}

CURRENT CODE:
{code}

CONTEXT:
{context}

Provide a minimal fix that resolves the issue without changing unrelated code.
Respond with ONLY the fixed code in markdown code blocks.`,
    REVIEW: `You are a senior code reviewer for the SENTINEL security platform.
Review the following changes for:
1. Security vulnerabilities
2. Logic errors
3. Performance issues
4. Code style violations

CHANGES:
{changes}

SPEC:
{spec}

Respond in JSON format:
{
  "approved": boolean,
  "issues": [{ "severity": "high|medium|low", "file": "...", "line": N, "message": "..." }],
  "suggestions": ["..."]
}`,
    TEST_GENERATE: `You are a test engineer for the SENTINEL platform.
Generate comprehensive unit tests for the following code.

CODE:
{code}

REQUIREMENTS:
{requirements}

Use the project's testing framework (Jest for TS, pytest for Python).
Cover edge cases and error scenarios.
Respond with ONLY the test code in markdown blocks.`
};
/**
 * Claude API Client
 */
class ClaudeAPIClient {
    constructor(config = {}) {
        this.apiKey = config.apiKey || process.env.ANTHROPIC_API_KEY || '';
        this.baseUrl = config.baseUrl || 'https://api.anthropic.com';
        this.defaultModel = config.defaultModel || 'claude-sonnet-4-20250514';
        this.defaultMaxTokens = config.defaultMaxTokens || 4096;
        this.timeout = config.timeout || 60000;
    }
    /**
     * Check if API key is configured
     */
    isConfigured() {
        return this.apiKey.length > 0;
    }
    /**
     * Send a message to Claude
     */
    async complete(request) {
        if (!this.isConfigured()) {
            throw new Error('Claude API key not configured. Set ANTHROPIC_API_KEY env variable.');
        }
        const body = {
            model: request.model || this.defaultModel,
            max_tokens: request.maxTokens || this.defaultMaxTokens,
            temperature: request.temperature ?? 0.3,
            system: request.systemPrompt || '',
            messages: [
                { role: 'user', content: request.prompt }
            ],
            stop_sequences: request.stopSequences
        };
        const response = await fetch(`${this.baseUrl}/v1/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': this.apiKey,
                'anthropic-version': '2023-06-01'
            },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(this.timeout)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Claude API error: ${response.status} - ${error}`);
        }
        const data = await response.json();
        return {
            content: data.content[0]?.text || '',
            model: data.model,
            stopReason: data.stop_reason,
            usage: {
                inputTokens: data.usage.input_tokens,
                outputTokens: data.usage.output_tokens
            }
        };
    }
    /**
     * Generate code implementation
     */
    async generateCode(task, spec, context = '') {
        const prompt = exports.PROMPTS.IMPLEMENT
            .replace('{task}', task)
            .replace('{spec}', spec)
            .replace('{context}', context);
        const response = await this.complete({
            prompt,
            temperature: 0.2 // Conservative for code gen
        });
        const files = this.parseCodeBlocks(response.content);
        return { code: response.content, files };
    }
    /**
     * Generate fix for an issue
     */
    async generateFix(issue, currentCode, context = '') {
        const prompt = exports.PROMPTS.FIX
            .replace('{issue}', issue)
            .replace('{code}', currentCode)
            .replace('{context}', context);
        const response = await this.complete({
            prompt,
            temperature: 0.1 // Very conservative for fixes
        });
        const files = this.parseCodeBlocks(response.content);
        return { code: response.content, files };
    }
    /**
     * Review code changes
     */
    async reviewCode(changes, spec) {
        const prompt = exports.PROMPTS.REVIEW
            .replace('{changes}', changes)
            .replace('{spec}', spec);
        const response = await this.complete({
            prompt,
            temperature: 0
        });
        try {
            // Extract JSON from response
            const jsonMatch = response.content.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        }
        catch {
            // Fallback if JSON parsing fails
        }
        return {
            approved: false,
            issues: [{ severity: 'high', file: '', line: 0, message: 'Failed to parse review response' }],
            suggestions: []
        };
    }
    /**
     * Generate tests
     */
    async generateTests(code, requirements) {
        const prompt = exports.PROMPTS.TEST_GENERATE
            .replace('{code}', code)
            .replace('{requirements}', requirements);
        const response = await this.complete({
            prompt,
            temperature: 0.3
        });
        const files = this.parseCodeBlocks(response.content);
        return { tests: response.content, files };
    }
    /**
     * Parse code blocks from response
     */
    parseCodeBlocks(content) {
        const files = [];
        // Match: ```language:path/to/file.ext or ```language
        const codeBlockRegex = /```(\w+)(?::([^\n]+))?\n([\s\S]*?)```/g;
        let match;
        while ((match = codeBlockRegex.exec(content)) !== null) {
            files.push({
                language: match[1],
                path: match[2] || null,
                content: match[3].trim()
            });
        }
        return files;
    }
    /**
     * Simple chat interface for swarm mode
     * @param prompt - The prompt to send
     * @param options - Options including model selection
     */
    async chat(prompt, options = {}) {
        const model = this.resolveModel(options.model);
        const response = await this.complete({
            prompt,
            model,
            maxTokens: options.maxTokens
        });
        return response.content;
    }
    /**
     * Resolve swarm model alias to full model name
     */
    resolveModel(model) {
        if (!model)
            return this.defaultModel;
        // Check if it's a swarm alias
        if (model in exports.SWARM_MODEL_MAP) {
            return exports.SWARM_MODEL_MAP[model];
        }
        // It's already a full model name
        return model;
    }
}
exports.ClaudeAPIClient = ClaudeAPIClient;
/**
 * Singleton instance for shared use
 */
let sharedClient = null;
function getClaudeClient(config) {
    if (!sharedClient) {
        sharedClient = new ClaudeAPIClient(config);
    }
    return sharedClient;
}
//# sourceMappingURL=ClaudeAPIClient.js.map