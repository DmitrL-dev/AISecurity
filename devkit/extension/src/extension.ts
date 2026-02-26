/**
 * SENTINEL DevKit Extension
 * Main entry point
 */

import * as vscode from 'vscode';
import { DevKitPanelProvider } from './panels/DevKitPanelProvider';

let panelProvider: DevKitPanelProvider | undefined;

/**
 * Called when extension is activated
 */
export function activate(context: vscode.ExtensionContext): void {
    console.log('SENTINEL DevKit extension is now active');

    // Register commands
    const openPanelCommand = vscode.commands.registerCommand(
        'sentinel-devkit.openPanel',
        () => {
            DevKitPanelProvider.createOrShow(context.extensionUri);
        }
    );

    const showKanbanCommand = vscode.commands.registerCommand(
        'sentinel-devkit.showKanban',
        () => {
            DevKitPanelProvider.createOrShow(context.extensionUri, 'kanban');
        }
    );

    // Register webview view provider for sidebar
    panelProvider = new DevKitPanelProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'sentinel-devkit.dashboard',
            panelProvider
        )
    );

    context.subscriptions.push(openPanelCommand);
    context.subscriptions.push(showKanbanCommand);
}

/**
 * Called when extension is deactivated
 */
export function deactivate(): void {
    console.log('SENTINEL DevKit extension deactivated');
}
