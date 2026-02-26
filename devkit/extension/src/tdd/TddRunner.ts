/**
 * TDD Runner
 * Runs npm test and parses results for TDD compliance metrics
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface TddStatus {
    compliance: number;      // 0-100%
    tests: number;           // total test count
    passed: number;          // passed tests
    failed: number;          // failed tests
    coverage: number;        // 0-100%
    lastRun: string;         // ISO timestamp
    hasTestConfig: boolean;  // package.json has test script
}

/**
 * TDD Runner - executes npm test and parses results
 */
export class TddRunner {
    private workspaceRoot: string;
    private lastStatus: TddStatus | null = null;

    constructor() {
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    }

    /**
     * Check if project has test configuration
     */
    hasTestConfig(): boolean {
        const packageJsonPath = path.join(this.workspaceRoot, 'package.json');
        
        if (!fs.existsSync(packageJsonPath)) {
            return false;
        }

        try {
            const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
            return packageJson.scripts?.test !== undefined;
        } catch {
            return false;
        }
    }

    /**
     * Get cached status or run tests
     */
    async getStatus(forceRun: boolean = false): Promise<TddStatus> {
        // Return cached if available and not forcing
        if (this.lastStatus && !forceRun) {
            return this.lastStatus;
        }

        // Check if test config exists
        if (!this.hasTestConfig()) {
            return {
                compliance: 0,
                tests: 0,
                passed: 0,
                failed: 0,
                coverage: 0,
                lastRun: new Date().toISOString(),
                hasTestConfig: false
            };
        }

        // Run tests
        return this.runTests();
    }

    /**
     * Run npm test and parse output
     */
    private async runTests(): Promise<TddStatus> {
        return new Promise((resolve) => {
            const startTime = Date.now();
            
            // Run npm test with JSON reporter if available
            const testCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
            
            const child = cp.spawn(testCmd, ['test', '--', '--reporter=json'], {
                cwd: this.workspaceRoot,
                shell: true,
                timeout: 60000
            });

            let stdout = '';
            let stderr = '';

            child.stdout?.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr?.on('data', (data) => {
                stderr += data.toString();
            });

            child.on('close', (code) => {
                const status = this.parseTestOutput(stdout + stderr, code === 0);
                status.lastRun = new Date().toISOString();
                status.hasTestConfig = true;
                this.lastStatus = status;
                resolve(status);
            });

            child.on('error', () => {
                resolve({
                    compliance: 0,
                    tests: 0,
                    passed: 0,
                    failed: 0,
                    coverage: 0,
                    lastRun: new Date().toISOString(),
                    hasTestConfig: true
                });
            });
        });
    }

    /**
     * Parse test output to extract metrics
     */
    private parseTestOutput(output: string, passed: boolean): TddStatus {
        let tests = 0;
        let passedTests = 0;
        let failedTests = 0;
        let coverage = 0;

        // Try to parse Jest output
        const jestMatch = output.match(/Tests:\s+(\d+)\s+passed,\s+(\d+)\s+total/);
        if (jestMatch) {
            passedTests = parseInt(jestMatch[1], 10);
            tests = parseInt(jestMatch[2], 10);
            failedTests = tests - passedTests;
        }

        // Try to parse Mocha output
        const mochaPassMatch = output.match(/(\d+)\s+passing/);
        const mochaFailMatch = output.match(/(\d+)\s+failing/);
        if (mochaPassMatch) {
            passedTests = parseInt(mochaPassMatch[1], 10);
            failedTests = mochaFailMatch ? parseInt(mochaFailMatch[1], 10) : 0;
            tests = passedTests + failedTests;
        }

        // Try to parse coverage
        const coverageMatch = output.match(/All files\s+\|\s+([\d.]+)/);
        if (coverageMatch) {
            coverage = parseFloat(coverageMatch[1]);
        }

        // Calculate compliance
        const compliance = tests > 0 ? Math.round((passedTests / tests) * 100) : 0;

        return {
            compliance,
            tests,
            passed: passedTests,
            failed: failedTests,
            coverage,
            lastRun: '',
            hasTestConfig: true
        };
    }

    /**
     * Get status for webview (formatted)
     */
    async getStatusForWebview(): Promise<{
        compliance: number;
        tests: number;
        coverage: number;
        hasTestConfig: boolean;
    }> {
        const status = await this.getStatus();
        return {
            compliance: status.compliance,
            tests: status.tests,
            coverage: status.coverage,
            hasTestConfig: status.hasTestConfig
        };
    }
}
