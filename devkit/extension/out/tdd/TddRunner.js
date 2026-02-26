"use strict";
/**
 * TDD Runner
 * Runs npm test and parses results for TDD compliance metrics
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
exports.TddRunner = void 0;
const vscode = __importStar(require("vscode"));
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
/**
 * TDD Runner - executes npm test and parses results
 */
class TddRunner {
    constructor() {
        this.lastStatus = null;
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    }
    /**
     * Check if project has test configuration
     */
    hasTestConfig() {
        const packageJsonPath = path.join(this.workspaceRoot, 'package.json');
        if (!fs.existsSync(packageJsonPath)) {
            return false;
        }
        try {
            const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
            return packageJson.scripts?.test !== undefined;
        }
        catch {
            return false;
        }
    }
    /**
     * Get cached status or run tests
     */
    async getStatus(forceRun = false) {
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
    async runTests() {
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
    parseTestOutput(output, passed) {
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
    async getStatusForWebview() {
        const status = await this.getStatus();
        return {
            compliance: status.compliance,
            tests: status.tests,
            coverage: status.coverage,
            hasTestConfig: status.hasTestConfig
        };
    }
}
exports.TddRunner = TddRunner;
//# sourceMappingURL=TddRunner.js.map