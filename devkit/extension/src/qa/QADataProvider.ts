/**
 * QA Data Provider
 * Provides QA Fix Loop status for webview
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export interface QAStatus {
    iteration: number;
    maxIterations: number;
    issues: {
        high: number;
        medium: number;
        low: number;
    };
    fixed: number;
    total: number;
    available: boolean;
}

/**
 * QA Data Provider - reads from .sentinel or uses defaults
 */
export class QADataProvider {
    private workspaceRoot: string;

    constructor() {
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    }

    /**
     * Get QA status from .sentinel directory or use defaults
     */
    async getStatus(): Promise<QAStatus> {
        const qaStatePath = path.join(this.workspaceRoot, '.sentinel', 'qa', 'state.json');
        
        // Try to read from state file
        if (fs.existsSync(qaStatePath)) {
            try {
                const state = JSON.parse(fs.readFileSync(qaStatePath, 'utf-8'));
                return {
                    iteration: state.iteration || 0,
                    maxIterations: state.maxIterations || 3,
                    issues: {
                        high: state.issues?.high || 0,
                        medium: state.issues?.medium || 0,
                        low: state.issues?.low || 0
                    },
                    fixed: state.fixed || 0,
                    total: (state.issues?.high || 0) + (state.issues?.medium || 0) + (state.issues?.low || 0),
                    available: true
                };
            } catch (error) {
                // Fall through to defaults
            }
        }

        // Check for lint/test errors in diagnostics
        const diagnostics = this.getDiagnosticsSummary();
        
        if (diagnostics.total > 0) {
            return {
                iteration: 1,
                maxIterations: 3,
                issues: diagnostics,
                fixed: 0,
                total: diagnostics.high + diagnostics.medium + diagnostics.low,
                available: true
            };
        }

        // No active QA session
        return {
            iteration: 0,
            maxIterations: 3,
            issues: { high: 0, medium: 0, low: 0 },
            fixed: 0,
            total: 0,
            available: false
        };
    }

    /**
     * Get summary from VS Code diagnostics
     */
    private getDiagnosticsSummary(): { high: number; medium: number; low: number; total: number } {
        let high = 0;
        let medium = 0;
        let low = 0;

        const allDiagnostics = vscode.languages.getDiagnostics();
        
        for (const [uri, diagnostics] of allDiagnostics) {
            // Skip node_modules and other external files
            if (uri.fsPath.includes('node_modules')) continue;

            for (const diag of diagnostics) {
                switch (diag.severity) {
                    case vscode.DiagnosticSeverity.Error:
                        high++;
                        break;
                    case vscode.DiagnosticSeverity.Warning:
                        medium++;
                        break;
                    case vscode.DiagnosticSeverity.Information:
                    case vscode.DiagnosticSeverity.Hint:
                        low++;
                        break;
                }
            }
        }

        return { high, medium, low, total: high + medium + low };
    }

    /**
     * Get status for webview
     */
    async getStatusForWebview(): Promise<QAStatus> {
        return this.getStatus();
    }
}
