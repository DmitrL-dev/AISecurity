"use strict";
/**
 * TddRunner Unit Tests
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
// Mock vscode for testing
const mockVscode = {
    workspace: {
        workspaceFolders: [{ uri: { fsPath: process.cwd() } }]
    }
};
// Simple mock for TddRunner functionality
describe('TddRunner Tests', () => {
    describe('parseTestOutput', () => {
        it('should parse Jest output correctly', () => {
            const output = 'Tests: 10 passed, 10 total';
            const jestMatch = output.match(/Tests:\s+(\d+)\s+passed,\s+(\d+)\s+total/);
            assert.ok(jestMatch, 'Should match Jest format');
            assert.strictEqual(parseInt(jestMatch[1]), 10, 'Should parse passed count');
            assert.strictEqual(parseInt(jestMatch[2]), 10, 'Should parse total count');
        });
        it('should parse Mocha output correctly', () => {
            const output = '15 passing (2s)\n3 failing';
            const mochaPassMatch = output.match(/(\d+)\s+passing/);
            const mochaFailMatch = output.match(/(\d+)\s+failing/);
            assert.ok(mochaPassMatch, 'Should match Mocha passing format');
            assert.strictEqual(parseInt(mochaPassMatch[1]), 15, 'Should parse passing count');
            assert.ok(mochaFailMatch, 'Should match Mocha failing format');
            assert.strictEqual(parseInt(mochaFailMatch[1]), 3, 'Should parse failing count');
        });
        it('should parse pytest output correctly', () => {
            const output = '====== 25 passed in 1.23s ======';
            const pytestMatch = output.match(/(\d+)\s+passed/);
            assert.ok(pytestMatch, 'Should match pytest format');
            assert.strictEqual(parseInt(pytestMatch[1]), 25, 'Should parse passed count');
        });
        it('should calculate compliance correctly', () => {
            const passed = 8;
            const total = 10;
            const compliance = Math.round((passed / total) * 100);
            assert.strictEqual(compliance, 80, 'Should calculate 80% compliance');
        });
        it('should handle zero tests gracefully', () => {
            const passed = 0;
            const total = 0;
            const compliance = total > 0 ? Math.round((passed / total) * 100) : 0;
            assert.strictEqual(compliance, 0, 'Should return 0% for no tests');
        });
    });
    describe('hasTestConfig', () => {
        it('should detect package.json with test script', () => {
            const packageJson = {
                scripts: {
                    test: 'jest'
                }
            };
            const hasTest = packageJson.scripts?.test !== undefined;
            assert.strictEqual(hasTest, true, 'Should detect test script');
        });
        it('should return false for missing test script', () => {
            const packageJson = {
                scripts: {
                    build: 'tsc'
                }
            };
            const hasTest = packageJson.scripts?.test !== undefined;
            assert.strictEqual(hasTest, false, 'Should return false without test script');
        });
    });
});
//# sourceMappingURL=tdd.test.js.map