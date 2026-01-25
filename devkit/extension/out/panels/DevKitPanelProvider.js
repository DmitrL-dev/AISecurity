"use strict";
/**
 * DevKit Panel Provider
 * Manages webview panel for DevKit dashboard
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
exports.DevKitPanelProvider = void 0;
const vscode = __importStar(require("vscode"));
const KiroSpecReader_1 = require("../sdd/KiroSpecReader");
const TddRunner_1 = require("../tdd/TddRunner");
const RlmBridge_1 = require("../rlm/RlmBridge");
const TasksReader_1 = require("../kanban/TasksReader");
const QADataProvider_1 = require("../qa/QADataProvider");
const SecurityScannerAgent_1 = require("../agents/SecurityScannerAgent");
const AgentOrchestrator_1 = require("../agents/AgentOrchestrator");
class DevKitPanelProvider {
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    /**
     * Create or show the DevKit panel
     */
    static createOrShow(extensionUri, view = "dashboard") {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;
        // If panel exists, show it
        if (DevKitPanelProvider.currentPanel) {
            DevKitPanelProvider.currentPanel.reveal(column);
            DevKitPanelProvider.currentPanel.webview.postMessage({
                command: "navigate",
                view,
            });
            return;
        }
        // Create new panel
        const panel = vscode.window.createWebviewPanel("devkitPanel", "SENTINEL DevKit", column || vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [extensionUri],
        });
        DevKitPanelProvider.currentPanel = panel;
        panel.webview.html = DevKitPanelProvider.getHtmlContent(panel.webview, extensionUri, view);
        // Handle messages from webview
        panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case "alert":
                    vscode.window.showInformationMessage(message.text);
                    return;
                case "navigate":
                    return;
                case "getSddStatus":
                    const sddStatus = await DevKitPanelProvider.specReader.getStatusForWebview();
                    panel.webview.postMessage({
                        command: "sddStatus",
                        data: sddStatus,
                    });
                    return;
                case "getTddStatus":
                    const tddStatus = await DevKitPanelProvider.tddRunner.getStatusForWebview();
                    panel.webview.postMessage({
                        command: "tddStatus",
                        data: tddStatus,
                    });
                    return;
                case "getRlmStatus":
                    const rlmStatus = await DevKitPanelProvider.rlmBridge.getStatusForWebview();
                    panel.webview.postMessage({
                        command: "rlmStatus",
                        data: rlmStatus,
                    });
                    return;
                case "getQaStatus":
                    const qaStatus = await DevKitPanelProvider.qaProvider.getStatusForWebview();
                    panel.webview.postMessage({
                        command: "qaStatus",
                        data: qaStatus,
                    });
                    return;
                case "getBrainStatus":
                    const brainStatus = await DevKitPanelProvider.securityScanner.checkConnection();
                    panel.webview.postMessage({
                        command: "brainStatus",
                        data: brainStatus,
                    });
                    return;
                case "getPipelineStatus":
                    const pipelineState = DevKitPanelProvider.orchestrator.getState();
                    const logs = DevKitPanelProvider.orchestrator.getLogs(50);
                    panel.webview.postMessage({
                        command: "pipelineStatus",
                        data: { ...pipelineState, logs },
                    });
                    return;
                case "pausePipeline":
                    DevKitPanelProvider.orchestrator.pause();
                    return;
                case "stopPipeline":
                    DevKitPanelProvider.orchestrator.stop();
                    return;
                case "getKanbanTasks":
                    try {
                        const kanbanData = await DevKitPanelProvider.tasksReader.getDataForWebview();
                        panel.webview.postMessage({
                            command: "kanbanTasks",
                            data: kanbanData,
                        });
                    }
                    catch (error) {
                        panel.webview.postMessage({
                            command: "kanbanTasks",
                            data: { columns: {}, specs: [], totalTasks: 0 },
                        });
                    }
                    return;
                case "openFile":
                    if (message.data?.filePath) {
                        const uri = vscode.Uri.file(message.data.filePath);
                        const lineNumber = message.data.lineNumber || 1;
                        vscode.window.showTextDocument(uri, {
                            selection: new vscode.Range(lineNumber - 1, 0, lineNumber - 1, 0),
                        });
                    }
                    return;
            }
        }, undefined, []);
        // Clean up when panel is closed
        panel.onDidDispose(() => {
            DevKitPanelProvider.currentPanel = undefined;
        }, null, []);
    }
    /**
     * WebviewViewProvider implementation for sidebar
     */
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };
        webviewView.webview.html = DevKitPanelProvider.getHtmlContent(webviewView.webview, this._extensionUri, "sidebar");
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case "openFullPanel":
                    DevKitPanelProvider.createOrShow(this._extensionUri, message.view);
                    return;
                case "getSddStatus":
                    const sddStatus = await DevKitPanelProvider.specReader.getStatusForWebview();
                    webviewView.webview.postMessage({
                        command: "sddStatus",
                        data: sddStatus,
                    });
                    return;
                case "getTddStatus":
                    const tddStatus = await DevKitPanelProvider.tddRunner.getStatusForWebview();
                    webviewView.webview.postMessage({
                        command: "tddStatus",
                        data: tddStatus,
                    });
                    return;
                case "getRlmStatus":
                    const rlmStatus = await DevKitPanelProvider.rlmBridge.getStatusForWebview();
                    webviewView.webview.postMessage({
                        command: "rlmStatus",
                        data: rlmStatus,
                    });
                    return;
                case "getQaStatus":
                    const qaStatusSidebar = await DevKitPanelProvider.qaProvider.getStatusForWebview();
                    webviewView.webview.postMessage({
                        command: "qaStatus",
                        data: qaStatusSidebar,
                    });
                    return;
                case "getKanbanTasks":
                    try {
                        const kanbanData = await DevKitPanelProvider.tasksReader.getDataForWebview();
                        webviewView.webview.postMessage({
                            command: "kanbanTasks",
                            data: kanbanData,
                        });
                    }
                    catch (error) {
                        webviewView.webview.postMessage({
                            command: "kanbanTasks",
                            data: { columns: {}, specs: [], totalTasks: 0 },
                        });
                    }
                    return;
                case "openFile":
                    vscode.window.showInformationMessage(`DevKit: Opening ${message.data?.filePath}:${message.data?.lineNumber}`);
                    if (message.data?.filePath) {
                        const uri = vscode.Uri.file(message.data.filePath);
                        const lineNumber = message.data.lineNumber || 1;
                        vscode.window.showTextDocument(uri, {
                            selection: new vscode.Range(lineNumber - 1, 0, lineNumber - 1, 0),
                        });
                    }
                    return;
            }
        });
    }
    /**
     * Generate HTML content for webview
     */
    static getHtmlContent(webview, extensionUri, view) {
        // Get URIs for resources
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "main.js"));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "style.css"));
        const nonce = getNonce();
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="${styleUri}" rel="stylesheet">
    <title>SENTINEL DevKit</title>
</head>
<body>
    <div id="root" data-view="${view}"></div>
    <script nonce="${nonce}">
        // Make vscode API available globally for main.js
        window.vscode = acquireVsCodeApi();
        window.initialView = '${view}';
    </script>
    <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.DevKitPanelProvider = DevKitPanelProvider;
DevKitPanelProvider.viewType = "sentinel-devkit.dashboard";
DevKitPanelProvider.specReader = new KiroSpecReader_1.KiroSpecReader();
DevKitPanelProvider.tddRunner = new TddRunner_1.TddRunner();
DevKitPanelProvider.rlmBridge = new RlmBridge_1.RlmBridge();
DevKitPanelProvider.tasksReader = new TasksReader_1.TasksReader();
DevKitPanelProvider.qaProvider = new QADataProvider_1.QADataProvider();
DevKitPanelProvider.securityScanner = new SecurityScannerAgent_1.SecurityScannerAgent();
DevKitPanelProvider.orchestrator = new AgentOrchestrator_1.AgentOrchestrator();
/**
 * Generate a nonce for CSP
 */
function getNonce() {
    let text = "";
    const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
//# sourceMappingURL=DevKitPanelProvider.js.map