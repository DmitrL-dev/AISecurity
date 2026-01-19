import * as vscode from 'vscode';
import { RLMDashboardProvider } from './dashboardProvider';
import { RLMStatusBar } from './statusBar';
import { RLMMcpClient } from './mcpClient';

let mcpClient: RLMMcpClient;
let statusBar: RLMStatusBar;

export function activate(context: vscode.ExtensionContext) {
    console.log('RLM-Toolkit extension activated');
    
    // Initialize MCP client
    mcpClient = new RLMMcpClient();
    
    // Initialize status bar
    statusBar = new RLMStatusBar();
    context.subscriptions.push(statusBar.statusBarItem);
    
    // Register sidebar webview
    const dashboardProvider = new RLMDashboardProvider(
        context.extensionUri,
        mcpClient
    );
    
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'rlm.dashboard',
            dashboardProvider
        )
    );
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('rlm.reindex', async () => {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "RLM: Indexing project...",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Starting..." });
                
                const result = await mcpClient.reindex();
                
                if (result.success) {
                    progress.report({ increment: 100, message: "Done!" });
                    vscode.window.showInformationMessage(
                        `RLM: Indexed ${result.files_indexed} files in ${result.duration?.toFixed(1)}s`
                    );
                    statusBar.update(result);
                    dashboardProvider.refresh();
                } else {
                    vscode.window.showErrorMessage(`RLM: ${result.error}`);
                }
            });
        }),
        
        vscode.commands.registerCommand('rlm.validate', async () => {
            const result = await mcpClient.validate();
            if (result.success) {
                vscode.window.showInformationMessage(
                    `RLM: ${result.health} - ${result.symbols.total_symbols} symbols`
                );
            }
        }),
        
        vscode.commands.registerCommand('rlm.showStatus', async () => {
            const result = await mcpClient.getStatus();
            if (result.success) {
                const msg = `RLM v${result.version}: ${result.index.crystals} files, ${formatTokens(result.index.tokens)} tokens`;
                vscode.window.showInformationMessage(msg);
            }
        }),
        
        vscode.commands.registerCommand('rlm.consolidateMemory', async () => {
            const result = await mcpClient.consolidateMemory();
            vscode.window.showInformationMessage('RLM: Memory consolidated');
        })
    );
    
    // Initial status update
    updateStatus();
}

async function updateStatus() {
    try {
        const status = await mcpClient.getStatus();
        if (status.success) {
            statusBar.update(status);
        }
    } catch (e) {
        console.error('RLM status update failed:', e);
    }
}

function formatTokens(tokens: number): string {
    if (tokens >= 1000000) {
        return `${(tokens / 1000000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
        return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
}

export function deactivate() {
    console.log('RLM-Toolkit extension deactivated');
}
