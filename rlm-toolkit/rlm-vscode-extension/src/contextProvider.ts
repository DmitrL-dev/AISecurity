/**
 * RLM Context Provider
 * 
 * Provides cached, auto-injected context for LLM prompts.
 * Solves the "amnesia" problem by ensuring project knowledge persists.
 */

import * as vscode from 'vscode';
import { RLMMcpClient, RLMResponse } from './mcpClient';

export interface ContextCache {
    context: string;
    timestamp: number;
    activeFile?: string;
    tokensEstimated: number;
}

export class RLMContextProvider {
    private mcpClient: RLMMcpClient;
    private cache: ContextCache | null = null;
    private cacheTTL = 5 * 60 * 1000; // 5 minutes
    private refreshTimer: NodeJS.Timeout | null = null;
    private onContextUpdateCallbacks: ((context: string) => void)[] = [];

    constructor(mcpClient: RLMMcpClient) {
        this.mcpClient = mcpClient;
        
        // Subscribe to active editor changes
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor) {
                this.onActiveEditorChange(editor.document.uri.fsPath);
            }
        });
        
        // Initial context load
        this.refreshContext();
        
        // Periodic refresh
        this.startPeriodicRefresh();
    }

    /**
     * Get formatted context for injection
     */
    public async getContext(activeFile?: string): Promise<string> {
        // Check cache validity
        if (this.cache && this.isCacheValid(activeFile)) {
            return this.cache.context;
        }

        // Fetch fresh context
        await this.refreshContext(activeFile);
        return this.cache?.context || 'No project context available.';
    }

    /**
     * Get context synchronously from cache (may be stale)
     */
    public getCachedContext(): string {
        return this.cache?.context || 'No project context available.';
    }

    /**
     * Force refresh context
     */
    public async refreshContext(activeFile?: string): Promise<void> {
        try {
            const file = activeFile || vscode.window.activeTextEditor?.document.uri.fsPath;
            const maxTokens = this.getMaxTokensSetting();

            const result = await this.mcpClient.autoInject(file, maxTokens);
            
            if (result.success && result.context) {
                this.cache = {
                    context: result.context,
                    timestamp: Date.now(),
                    activeFile: file,
                    tokensEstimated: result.tokens_estimated || 0,
                };

                // Notify listeners
                this.onContextUpdateCallbacks.forEach(cb => cb(result.context));
            }
        } catch (error) {
            console.error('RLM: Failed to refresh context:', error);
        }
    }

    /**
     * Check if cache is still valid
     */
    private isCacheValid(activeFile?: string): boolean {
        if (!this.cache) return false;
        
        const now = Date.now();
        const isExpired = now - this.cache.timestamp > this.cacheTTL;
        
        // Invalidate if file changed (unless no file provided)
        const fileChanged = activeFile && this.cache.activeFile !== activeFile;
        
        return !isExpired && !fileChanged;
    }

    /**
     * Handle active editor change
     */
    private async onActiveEditorChange(filePath: string): Promise<void> {
        // Only refresh if file is in a different domain
        if (this.cache?.activeFile) {
            const oldDomain = this.extractDomain(this.cache.activeFile);
            const newDomain = this.extractDomain(filePath);
            
            if (oldDomain !== newDomain) {
                await this.refreshContext(filePath);
            }
        } else {
            await this.refreshContext(filePath);
        }
    }

    /**
     * Extract domain from file path (simple heuristic)
     */
    private extractDomain(filePath: string): string {
        const parts = filePath.replace(/\\/g, '/').split('/');
        // Return parent folder as domain proxy
        return parts[parts.length - 2] || 'unknown';
    }

    /**
     * Start periodic context refresh
     */
    private startPeriodicRefresh(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            this.refreshContext();
        }, this.cacheTTL);
    }

    /**
     * Get max tokens from settings
     */
    private getMaxTokensSetting(): number {
        const config = vscode.workspace.getConfiguration('rlm');
        return config.get<number>('autoContext.maxTokens', 2000);
    }

    /**
     * Check if auto-context is enabled
     */
    public isEnabled(): boolean {
        const config = vscode.workspace.getConfiguration('rlm');
        return config.get<boolean>('autoContext.enabled', true);
    }

    /**
     * Subscribe to context updates
     */
    public onContextUpdate(callback: (context: string) => void): void {
        this.onContextUpdateCallbacks.push(callback);
    }

    /**
     * Get cache stats
     */
    public getStats(): { cached: boolean; age: number; tokens: number } {
        if (!this.cache) {
            return { cached: false, age: 0, tokens: 0 };
        }
        
        return {
            cached: true,
            age: Math.floor((Date.now() - this.cache.timestamp) / 1000),
            tokens: this.cache.tokensEstimated,
        };
    }

    /**
     * Copy context to clipboard
     */
    public async copyToClipboard(): Promise<void> {
        const context = await this.getContext();
        await vscode.env.clipboard.writeText(context);
        vscode.window.showInformationMessage('RLM: Context copied to clipboard');
    }

    /**
     * Cleanup
     */
    public dispose(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
    }
}
