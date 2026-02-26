"use strict";
/**
 * QA Data Provider
 * Provides QA Fix Loop status for webview
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.QADataProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
/**
 * QA Data Provider - reads from .sentinel or uses defaults
 */
class QADataProvider {
    constructor() {
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    }
    /**
     * Get QA status from .sentinel directory or use defaults
     */
    async getStatus() {
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
            }
            catch (error) {
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
    getDiagnosticsSummary() {
        let high = 0;
        let medium = 0;
        let low = 0;
        const allDiagnostics = vscode.languages.getDiagnostics();
        for (const [uri, diagnostics] of allDiagnostics) {
            // Skip node_modules and other external files
            if (uri.fsPath.includes('node_modules'))
                continue;
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
    async getStatusForWebview() {
        return this.getStatus();
    }
}
exports.QADataProvider = QADataProvider;
//# sourceMappingURL=QADataProvider.js.map