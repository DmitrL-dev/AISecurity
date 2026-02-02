/**
 * GoMCP Client for RLM Toolkit VSCode Extension
 * 
 * This client replaces the Python spawn approach with a persistent
 * connection to gomcp-server via stdio.
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';

interface JsonRpcRequest {
    jsonrpc: '2.0';
    id: number;
    method: string;
    params?: any;
}

interface JsonRpcResponse {
    jsonrpc: '2.0';
    id: number;
    result?: any;
    error?: {
        code: number;
        message: string;
    };
}

interface PendingRequest {
    resolve: (value: any) => void;
    reject: (error: Error) => void;
    timeout: NodeJS.Timeout;
}

export class GoMCPClient {
    private process: ChildProcess | null = null;
    private requestId = 0;
    private pending: Map<number, PendingRequest> = new Map();
    private projectRoot: string;
    private serverPath: string;
    private pythonPath: string;
    private workerPath: string;
    private started = false;
    private rl: readline.Interface | null = null;

    constructor(options: {
        projectRoot: string;
        serverPath?: string;
        pythonPath?: string;
        workerPath?: string;
    }) {
        this.projectRoot = options.projectRoot;
        this.serverPath = options.serverPath || this.findServerPath();
        this.pythonPath = options.pythonPath || 'python';
        this.workerPath = options.workerPath || path.join(this.projectRoot, 'rlm_worker.py');
    }

    /**
     * Find the gomcp-server binary
     */
    private findServerPath(): string {
        const candidates = [
            // Extension bundled
            path.join(__dirname, '..', 'bin', 'rlm-mcp-server.exe'),
            path.join(__dirname, '..', 'bin', 'rlm-mcp-server'),
            // Global install
            'rlm-mcp-server',
            // Development
            path.join(this.projectRoot, 'gomcp', 'bin', 'rlm-mcp-server.exe'),
        ];

        for (const p of candidates) {
            if (fs.existsSync(p)) {
                return p;
            }
        }

        // Fallback to PATH
        return 'rlm-mcp-server';
    }

    /**
     * Start the GoMCP server process
     */
    async start(): Promise<void> {
        if (this.started) {
            return;
        }

        return new Promise((resolve, reject) => {
            try {
                this.process = spawn(this.serverPath, [
                    '--mode=stdio',
                    `--project=${this.projectRoot}`,
                    `--python=${this.pythonPath}`,
                    `--worker=${this.workerPath}`,
                ], {
                    cwd: this.projectRoot,
                    stdio: ['pipe', 'pipe', 'pipe'],
                });

                if (!this.process.stdout || !this.process.stdin) {
                    reject(new Error('Failed to create stdio pipes'));
                    return;
                }

                // Set up line reader for responses
                this.rl = readline.createInterface({
                    input: this.process.stdout,
                    crlfDelay: Infinity,
                });

                this.rl.on('line', (line) => {
                    this.handleResponse(line);
                });

                this.process.stderr?.on('data', (data) => {
                    console.error('[GoMCP stderr]', data.toString());
                });

                this.process.on('error', (err) => {
                    console.error('[GoMCP error]', err);
                    this.started = false;
                });

                this.process.on('close', (code) => {
                    console.log('[GoMCP closed]', code);
                    this.started = false;
                    this.cleanup();
                });

                this.started = true;

                // Initialize the server
                this.call('initialize', {
                    protocolVersion: '2025-11-25',
                    clientInfo: {
                        name: 'rlm-toolkit-vscode',
                        version: '2.1.0',
                    },
                }).then(resolve).catch(reject);

            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Stop the server process
     */
    stop(): void {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        this.cleanup();
        this.started = false;
    }

    /**
     * Clean up pending requests
     */
    private cleanup(): void {
        for (const [id, pending] of this.pending) {
            clearTimeout(pending.timeout);
            pending.reject(new Error('Connection closed'));
        }
        this.pending.clear();
        
        if (this.rl) {
            this.rl.close();
            this.rl = null;
        }
    }

    /**
     * Handle incoming JSON-RPC response
     */
    private handleResponse(line: string): void {
        try {
            const response: JsonRpcResponse = JSON.parse(line);
            const pending = this.pending.get(response.id);
            
            if (pending) {
                clearTimeout(pending.timeout);
                this.pending.delete(response.id);
                
                if (response.error) {
                    pending.reject(new Error(response.error.message));
                } else {
                    pending.resolve(response.result);
                }
            }
        } catch (err) {
            console.error('[GoMCP] Failed to parse response:', line);
        }
    }

    /**
     * Send a JSON-RPC request
     */
    private call<T = any>(method: string, params?: any, timeoutMs = 60000): Promise<T> {
        return new Promise((resolve, reject) => {
            if (!this.process?.stdin) {
                reject(new Error('Server not started'));
                return;
            }

            const id = ++this.requestId;
            const request: JsonRpcRequest = {
                jsonrpc: '2.0',
                id,
                method,
                params,
            };

            const timeout = setTimeout(() => {
                this.pending.delete(id);
                reject(new Error(`Request timeout: ${method}`));
            }, timeoutMs);

            this.pending.set(id, { resolve, reject, timeout });

            const json = JSON.stringify(request) + '\n';
            this.process.stdin.write(json);
        });
    }

    // ========== RLM Tools ==========

    async getStatus(): Promise<any> {
        return this.callTool('rlm_status', {});
    }

    async healthCheck(): Promise<any> {
        return this.callTool('rlm_health_check', {});
    }

    async getHierarchyStats(): Promise<any> {
        return this.callTool('rlm_get_hierarchy_stats', {});
    }

    async discoverProject(taskHint?: string): Promise<any> {
        return this.callTool('rlm_discover_project', {
            project_root: this.projectRoot,
            task_hint: taskHint,
        });
    }

    async enterpriseContext(query: string, maxTokens = 3000): Promise<any> {
        return this.callTool('rlm_enterprise_context', {
            query,
            max_tokens: maxTokens,
            include_causal: true,
        });
    }

    async reindex(force = false): Promise<any> {
        return this.callTool('rlm_reindex', {
            path: this.projectRoot,
            force,
        });
    }

    async addFact(content: string, level = 1, domain?: string): Promise<any> {
        return this.callTool('rlm_add_hierarchical_fact', {
            content,
            level,
            domain,
        });
    }

    async searchFacts(query: string, topK = 10): Promise<any> {
        return this.callTool('rlm_search_facts', {
            query,
            top_k: topK,
        });
    }

    async listTools(): Promise<any> {
        return this.call('tools/list');
    }

    private async callTool(name: string, args: any): Promise<any> {
        return this.call('tools/call', {
            name,
            arguments: args,
        });
    }

    /**
     * Check if server is running
     */
    isRunning(): boolean {
        return this.started && this.process !== null;
    }
}

/**
 * Drop-in replacement for RLMMcpClient
 * Falls back to Python spawn if GoMCP server is unavailable
 */
export class RLMHybridClient {
    private goClient: GoMCPClient | null = null;
    private projectRoot: string;
    private useGoMcp: boolean;

    constructor(projectRoot: string, useGoMcp = true) {
        this.projectRoot = projectRoot;
        this.useGoMcp = useGoMcp;
    }

    async initialize(): Promise<void> {
        if (this.useGoMcp) {
            try {
                this.goClient = new GoMCPClient({ projectRoot: this.projectRoot });
                await this.goClient.start();
                console.log('[RLM] Using GoMCP backend');
            } catch (err) {
                console.warn('[RLM] GoMCP unavailable, falling back to Python:', err);
                this.goClient = null;
            }
        }
    }

    async getStatus(): Promise<any> {
        if (this.goClient?.isRunning()) {
            return this.goClient.getStatus();
        }
        return this.fallbackPython('rlm_status', {});
    }

    async healthCheck(): Promise<any> {
        if (this.goClient?.isRunning()) {
            return this.goClient.healthCheck();
        }
        return this.fallbackPython('rlm_health_check', {});
    }

    async discoverProject(): Promise<any> {
        if (this.goClient?.isRunning()) {
            return this.goClient.discoverProject();
        }
        return this.fallbackPython('rlm_discover_project', {});
    }

    async enterpriseContext(query: string): Promise<any> {
        if (this.goClient?.isRunning()) {
            return this.goClient.enterpriseContext(query);
        }
        return this.fallbackPython('rlm_enterprise_context', { query });
    }

    async reindex(force = false): Promise<any> {
        if (this.goClient?.isRunning()) {
            return this.goClient.reindex(force);
        }
        return this.fallbackPython('rlm_reindex', { force });
    }

    stop(): void {
        this.goClient?.stop();
    }

    /**
     * Fallback to Python spawn (legacy behavior)
     */
    private async fallbackPython(tool: string, params: any): Promise<any> {
        // This would contain the original Python spawn logic
        // For now, throw to indicate fallback needed
        throw new Error(`Python fallback not implemented for ${tool}`);
    }
}
