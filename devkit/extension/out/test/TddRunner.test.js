"use strict";
/**
 * TddRunner Unit Tests
 * Tests for test output parsing and compliance calculation
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
// Parse logic extracted for testing (same as TddRunner.parseTestOutput)
function parseTestOutput(output, passed) {
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
describe('TddRunner', () => {
    describe('parseTestOutput', () => {
        it('should parse Jest output format', () => {
            const output = `PASS src/test/example.test.ts
Tests: 10 passed, 10 total`;
            const status = parseTestOutput(output, true);
            assert.strictEqual(status.tests, 10);
            assert.strictEqual(status.passed, 10);
            assert.strictEqual(status.failed, 0);
            assert.strictEqual(status.compliance, 100);
        });
        it('should parse Jest output with failures', () => {
            const output = `FAIL src/test/example.test.ts
Tests: 7 passed, 10 total`;
            const status = parseTestOutput(output, false);
            assert.strictEqual(status.tests, 10);
            assert.strictEqual(status.passed, 7);
            assert.strictEqual(status.failed, 3);
            assert.strictEqual(status.compliance, 70);
        });
        it('should parse Mocha output format', () => {
            const output = `  5 passing (123ms)`;
            const status = parseTestOutput(output, true);
            assert.strictEqual(status.tests, 5);
            assert.strictEqual(status.passed, 5);
            assert.strictEqual(status.failed, 0);
        });
        it('should parse Mocha output with failures', () => {
            const output = `  8 passing (200ms)
  2 failing`;
            const status = parseTestOutput(output, false);
            assert.strictEqual(status.tests, 10);
            assert.strictEqual(status.passed, 8);
            assert.strictEqual(status.failed, 2);
            assert.strictEqual(status.compliance, 80);
        });
        it('should parse coverage percentage', () => {
            const output = `All files |   85.5 | ...`;
            const status = parseTestOutput(output, true);
            assert.strictEqual(status.coverage, 85.5);
        });
        it('should return 0 compliance for no tests', () => {
            const output = `No tests found`;
            const status = parseTestOutput(output, false);
            assert.strictEqual(status.tests, 0);
            assert.strictEqual(status.compliance, 0);
        });
    });
    describe('compliance calculation', () => {
        it('should calculate 100% for all passing', () => {
            const passed = 20;
            const total = 20;
            const compliance = Math.round((passed / total) * 100);
            assert.strictEqual(compliance, 100);
        });
        it('should calculate 50% for half passing', () => {
            const passed = 5;
            const total = 10;
            const compliance = Math.round((passed / total) * 100);
            assert.strictEqual(compliance, 50);
        });
        it('should round compliance to integer', () => {
            const passed = 7;
            const total = 9;
            const compliance = Math.round((passed / total) * 100);
            assert.strictEqual(compliance, 78); // 77.77... rounds to 78
        });
    });
});
//# sourceMappingURL=TddRunner.test.js.map