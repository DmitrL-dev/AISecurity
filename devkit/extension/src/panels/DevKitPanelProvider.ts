/**
 * DevKit Panel Provider
 * Manages webview panel for DevKit dashboard
 */

import * as vscode from "vscode";
import { KiroSpecReader } from "../sdd/KiroSpecReader";
import { TddRunner } from "../tdd/TddRunner";
import { RlmBridge } from "../rlm/RlmBridge";
import { TasksReader } from "../kanban/TasksReader";
import { QADataProvider } from "../qa/QADataProvider";
import { SecurityScannerAgent } from "../agents/SecurityScannerAgent";
import { AgentOrchestrator } from "../agents/AgentOrchestrator";

export class DevKitPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "sentinel-devkit.dashboard";

  private static currentPanel: vscode.WebviewPanel | undefined;
  private static specReader: KiroSpecReader = new KiroSpecReader();
  private static tddRunner: TddRunner = new TddRunner();
  private static rlmBridge: RlmBridge = new RlmBridge();
  private static tasksReader: TasksReader = new TasksReader();
  private static qaProvider: QADataProvider = new QADataProvider();
  private static securityScanner: SecurityScannerAgent = new SecurityScannerAgent();
  private static orchestrator: AgentOrchestrator = new AgentOrchestrator();
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  /**
   * Create or show the DevKit panel
   */
  public static createOrShow(
    extensionUri: vscode.Uri,
    view: string = "dashboard",
  ): void {
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
    const panel = vscode.window.createWebviewPanel(
      "devkitPanel",
      "SENTINEL DevKit",
      column || vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [extensionUri],
      },
    );

    DevKitPanelProvider.currentPanel = panel;
    panel.webview.html = DevKitPanelProvider.getHtmlContent(
      panel.webview,
      extensionUri,
      view,
    );

    // Handle messages from webview
    panel.webview.onDidReceiveMessage(
      async (message) => {
        switch (message.command) {
          case "alert":
            vscode.window.showInformationMessage(message.text);
            return;
          case "navigate":
            return;
          case "getSddStatus":
            const sddStatus =
              await DevKitPanelProvider.specReader.getStatusForWebview();
            panel.webview.postMessage({
              command: "sddStatus",
              data: sddStatus,
            });
            return;
          case "getTddStatus":
            const tddStatus =
              await DevKitPanelProvider.tddRunner.getStatusForWebview();
            panel.webview.postMessage({
              command: "tddStatus",
              data: tddStatus,
            });
            return;
          case "getRlmStatus":
            const rlmStatus =
              await DevKitPanelProvider.rlmBridge.getStatusForWebview();
            panel.webview.postMessage({
              command: "rlmStatus",
              data: rlmStatus,
            });
            return;
          case "getQaStatus":
            const qaStatus =
              await DevKitPanelProvider.qaProvider.getStatusForWebview();
            panel.webview.postMessage({
              command: "qaStatus",
              data: qaStatus,
            });
            return;
          case "getBrainStatus":
            const brainStatus =
              await DevKitPanelProvider.securityScanner.checkConnection();
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
              const kanbanData =
                await DevKitPanelProvider.tasksReader.getDataForWebview();
              panel.webview.postMessage({
                command: "kanbanTasks",
                data: kanbanData,
              });
            } catch (error: any) {
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
      },
      undefined,
      [],
    );

    // Clean up when panel is closed
    panel.onDidDispose(
      () => {
        DevKitPanelProvider.currentPanel = undefined;
      },
      null,
      [],
    );
  }

  /**
   * WebviewViewProvider implementation for sidebar
   */
  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri],
    };

    webviewView.webview.html = DevKitPanelProvider.getHtmlContent(
      webviewView.webview,
      this._extensionUri,
      "sidebar",
    );

    webviewView.webview.onDidReceiveMessage(async (message) => {
      switch (message.command) {
        case "openFullPanel":
          DevKitPanelProvider.createOrShow(this._extensionUri, message.view);
          return;
        case "getSddStatus":
          const sddStatus =
            await DevKitPanelProvider.specReader.getStatusForWebview();
          webviewView.webview.postMessage({
            command: "sddStatus",
            data: sddStatus,
          });
          return;
        case "getTddStatus":
          const tddStatus =
            await DevKitPanelProvider.tddRunner.getStatusForWebview();
          webviewView.webview.postMessage({
            command: "tddStatus",
            data: tddStatus,
          });
          return;
        case "getRlmStatus":
          const rlmStatus =
            await DevKitPanelProvider.rlmBridge.getStatusForWebview();
          webviewView.webview.postMessage({
            command: "rlmStatus",
            data: rlmStatus,
          });
          return;
        case "getQaStatus":
          const qaStatusSidebar =
            await DevKitPanelProvider.qaProvider.getStatusForWebview();
          webviewView.webview.postMessage({
            command: "qaStatus",
            data: qaStatusSidebar,
          });
          return;
        case "getKanbanTasks":
          try {
            const kanbanData =
              await DevKitPanelProvider.tasksReader.getDataForWebview();
            webviewView.webview.postMessage({
              command: "kanbanTasks",
              data: kanbanData,
            });
          } catch (error: any) {
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
  private static getHtmlContent(
    webview: vscode.Webview,
    extensionUri: vscode.Uri,
    view: string,
  ): string {
    // Get URIs for resources
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "media", "main.js"),
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "media", "style.css"),
    );

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

/**
 * Generate a nonce for CSP
 */
function getNonce(): string {
  let text = "";
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
