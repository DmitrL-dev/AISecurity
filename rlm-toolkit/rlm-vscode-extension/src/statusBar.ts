import * as vscode from 'vscode';

export class RLMStatusBar {
    public readonly statusBarItem: vscode.StatusBarItem;
    
    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        
        this.statusBarItem.command = 'rlm.showStatus';
        this.statusBarItem.tooltip = 'RLM-Toolkit - Click for status';
        this.statusBarItem.text = '$(crystal) RLM';
        this.statusBarItem.show();
    }
    
    public update(status: any) {
        if (status.success) {
            const crystals = status.index?.crystals || 0;
            const tokens = this.formatTokens(status.index?.tokens || 0);
            this.statusBarItem.text = `$(crystal) RLM: ${crystals} files | ${tokens}`;
            this.statusBarItem.backgroundColor = undefined;
        } else {
            this.statusBarItem.text = '$(crystal) RLM: Error';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.errorBackground'
            );
        }
    }
    
    private formatTokens(tokens: number): string {
        if (tokens >= 1000000) {
            return `${(tokens / 1000000).toFixed(1)}M`;
        } else if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(0)}K`;
        }
        return tokens.toString();
    }
}
