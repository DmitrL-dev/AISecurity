/**
 * SENTINEL DevKit Extension - Test Suite
 * TDD: Tests first, then implementation
 */

import * as assert from 'assert';
import * as vscode from 'vscode';

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
        assert.ok(
            commands.includes('sentinel-devkit.openPanel'),
            'openPanel command should be registered'
        );
    });

    test('Command sentinel-devkit.showKanban should be registered', async () => {
        // RED: This test will fail until command is registered
        const commands = await vscode.commands.getCommands(true);
        assert.ok(
            commands.includes('sentinel-devkit.showKanban'),
            'showKanban command should be registered'
        );
    });
});

suite('DevKit Panel Test Suite', () => {
    test('Panel should open on command', async () => {
        // RED: This test will fail until panel is implemented
        try {
            await vscode.commands.executeCommand('sentinel-devkit.openPanel');
            // If no error, command executed successfully
            assert.ok(true, 'Panel command executed');
        } catch (error) {
            assert.fail('Panel command should not throw');
        }
    });
});
