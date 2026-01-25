"use strict";
/**
 * SENTINEL DevKit Extension - Test Suite
 * TDD: Tests first, then implementation
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
const assert = __importStar(require("assert"));
const vscode = __importStar(require("vscode"));
suite('DevKit Extension Test Suite', () => {
    vscode.window.showInformationMessage('Starting DevKit tests...');
    test('Extension should be present', () => {
        // RED: This test will fail until extension is properly registered
        const extension = vscode.extensions.getExtension('sentinel.sentinel-devkit');
        assert.ok(extension, 'Extension should be installed');
    });
    test('Extension should activate', async () => {
        // RED: This test will fail until extension activates
        const extension = vscode.extensions.getExtension('sentinel.sentinel-devkit');
        if (extension) {
            await extension.activate();
            assert.strictEqual(extension.isActive, true, 'Extension should be active');
        }
    });
    test('Command sentinel-devkit.openPanel should be registered', async () => {
        // RED: This test will fail until command is registered
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('sentinel-devkit.openPanel'), 'openPanel command should be registered');
    });
    test('Command sentinel-devkit.showKanban should be registered', async () => {
        // RED: This test will fail until command is registered
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('sentinel-devkit.showKanban'), 'showKanban command should be registered');
    });
});
suite('DevKit Panel Test Suite', () => {
    test('Panel should open on command', async () => {
        // RED: This test will fail until panel is implemented
        try {
            await vscode.commands.executeCommand('sentinel-devkit.openPanel');
            // If no error, command executed successfully
            assert.ok(true, 'Panel command executed');
        }
        catch (error) {
            assert.fail('Panel command should not throw');
        }
    });
});
//# sourceMappingURL=extension.test.js.map