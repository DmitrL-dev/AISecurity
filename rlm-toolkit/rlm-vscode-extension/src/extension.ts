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
        }),
        
        // v2.1 Enterprise commands
        vscode.commands.registerCommand('rlm.discoverProject', async () => {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "RLM: Discovering project...",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Cold start analysis..." });
                
                const result = await mcpClient.discoverProject();
                
                if (result.success) {
                    progress.report({ increment: 100, message: "Done!" });
                    const facts = result.facts_created || 0;
                    const domains = result.suggested_domains?.length || 0;
                    vscode.window.showInformationMessage(
                        `RLM: Discovered ${facts} facts, ${domains} domains`
                    );
                    dashboardProvider.refresh();
                } else {
                    vscode.window.showErrorMessage(`RLM: ${result.error}`);
                }
            });
        }),
        
        vscode.commands.registerCommand('rlm.enterpriseQuery', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Enter your query for enterprise context',
                placeHolder: 'e.g., Explain the authentication architecture'
            });
            
            if (query) {
                const result = await mcpClient.enterpriseContext(query);
                if (result.success) {
                    const doc = await vscode.workspace.openTextDocument({
                        content: result.context || 'No context found',
                        language: 'markdown'
                    });
                    await vscode.window.showTextDocument(doc);
                }
            }
        }),
        
        vscode.commands.registerCommand('rlm.healthCheck', async () => {
            const result = await mcpClient.healthCheck();
            if (result.success) {
                const components = result.components || {};
                const store = components.store?.status || 'unknown';
                const router = components.router?.status || 'unknown';
                vscode.window.showInformationMessage(
                    `RLM Health: Store=${store}, Router=${router}`
                );
            } else {
                vscode.window.showErrorMessage(`RLM: ${result.error}`);
            }
        }),
        
        vscode.commands.registerCommand('rlm.installGitHook', async () => {
            const result = await mcpClient.installGitHook();
            if (result.success) {
                vscode.window.showInformationMessage('RLM: Git hook installed for auto-extraction');
            } else {
                vscode.window.showErrorMessage(`RLM: ${result.error}`);
            }
        }),
        
        vscode.commands.registerCommand('rlm.indexEmbeddings', async () => {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "RLM: Indexing embeddings...",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Generating embeddings..." });
                
                const result = await mcpClient.indexEmbeddings();
                
                if (result.success) {
                    progress.report({ increment: 100, message: "Done!" });
                    const indexed = result.indexed_count || 0;
                    vscode.window.showInformationMessage(
                        `RLM: Indexed ${indexed} embeddings for semantic routing`
                    );
                    dashboardProvider.refresh();
                } else {
                    vscode.window.showErrorMessage(`RLM: ${result.error}`);
                }
            });
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
