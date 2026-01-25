"use strict";
/**
 * SENTINEL DevKit Extension
 * Main entry point
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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const DevKitPanelProvider_1 = require("./panels/DevKitPanelProvider");
let panelProvider;
/**
 * Called when extension is activated
 */
function activate(context) {
    console.log('SENTINEL DevKit extension is now active');
    // Register commands
    const openPanelCommand = vscode.commands.registerCommand('sentinel-devkit.openPanel', () => {
        DevKitPanelProvider_1.DevKitPanelProvider.createOrShow(context.extensionUri);
    });
    const showKanbanCommand = vscode.commands.registerCommand('sentinel-devkit.showKanban', () => {
        DevKitPanelProvider_1.DevKitPanelProvider.createOrShow(context.extensionUri, 'kanban');
    });
    // Register webview view provider for sidebar
    panelProvider = new DevKitPanelProvider_1.DevKitPanelProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('sentinel-devkit.dashboard', panelProvider));
    context.subscriptions.push(openPanelCommand);
    context.subscriptions.push(showKanbanCommand);
}
/**
 * Called when extension is deactivated
 */
function deactivate() {
    console.log('SENTINEL DevKit extension deactivated');
}
//# sourceMappingURL=extension.js.map