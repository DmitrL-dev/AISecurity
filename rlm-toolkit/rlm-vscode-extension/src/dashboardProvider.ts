import * as vscode from 'vscode';
import { RLMMcpClient } from './mcpClient';
import {
    extractDashboardData,
    renderDashboardHtml,
    formatTokens as fmtTokens,
} from './dashboardTemplate';

export class RLMDashboardProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    
    constructor(
        private readonly extensionUri: vscode.Uri,
        private readonly mcpClient: RLMMcpClient
    ) {}
    
    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };
        
        this.updateContent();
        
        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'reindex':
                    await vscode.commands.executeCommand('rlm.reindex');
                    this.refresh();
                    break;
                case 'validate':
                    await vscode.commands.executeCommand('rlm.validate');
                    this.refresh();
                    break;
                case 'consolidate':
                    await vscode.commands.executeCommand('rlm.consolidateMemory');
                    this.refresh();
                    break;
                case 'refresh':
                    this.refresh();
                    break;
                // v2.1 Enterprise commands
                case 'discover':
                    await vscode.commands.executeCommand('rlm.discoverProject');
                    this.refresh();
                    break;
                case 'gitHook':
                    await vscode.commands.executeCommand('rlm.installGitHook');
                    this.refresh();
                    break;
                case 'indexEmbeddings':
                    await vscode.commands.executeCommand('rlm.indexEmbeddings');
                    this.refresh();
                    break;
                case 'switchProject':
                    if (message.path) {
                        this.mcpClient.setProjectRoot(message.path);
                        this.refresh();
                    }
                    break;
            }
        });
    }
    
    public async refresh() {
        await this.updateContent();
    }
    
    private async updateContent() {
        if (!this._view) return;
        
        // Get status from MCP (v1.x)
        const status = await this.mcpClient.getStatus();
        const validation = await this.mcpClient.validate();
        const sessionStats = await this.mcpClient.getSessionStats();
        const workspaceFolders = this.mcpClient.getWorkspaceFolders();
        const currentProject = this.mcpClient.getProjectRoot();
        
        // Get v2.1 data
        const healthCheck = await this.mcpClient.healthCheck();
        const hierarchyStats = await this.mcpClient.getHierarchyStats();
        
        this._view.webview.html = this.getHtml(
            status, validation, sessionStats, 
            workspaceFolders, currentProject,
            healthCheck, hierarchyStats
        );
    }
    
    private getHtml(
        status: any, validation: any, sessionStats: any, 
        workspaceFolders: {name: string, path: string}[] = [], 
        currentProject: string = '',
        healthCheck: any = {},
        hierarchyStats: any = {}
    ): string {
        const data = extractDashboardData(
            status, validation, sessionStats,
            healthCheck, hierarchyStats,
            workspaceFolders, currentProject,
        );
        return renderDashboardHtml(data);
    }
    
    private formatTokens(tokens: number): string {
        return fmtTokens(tokens);
    }
}
