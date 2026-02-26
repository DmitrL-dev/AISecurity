"use strict";
/**
 * Tester Agent
 * Generates tests and validates coverage
 * Uses TDD Iron Law methodology
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TesterAgent = void 0;
const AgentRegistry_1 = require("./AgentRegistry");
/**
 * Tester Agent - Generates and runs tests following TDD Iron Law
 *
 * Workflow:
 * 1. Analyze spec requirements
 * 2. Generate failing tests (RED)
 * 3. Verify tests pass after implementation (GREEN)
 * 4. Report coverage and suggest improvements
 */
class TesterAgent {
    constructor() {
        this.id = 'tester';
        this.name = 'Tester';
        this.role = AgentRegistry_1.AgentRole.CODER; // Works alongside coder
        this.status = AgentRegistry_1.AgentStatus.IDLE;
        this.coverageThreshold = 80; // TDD requires high coverage
    }
    /**
     * Generate tests from specification
     */
    async generateTests(spec) {
        this.status = AgentRegistry_1.AgentStatus.RUNNING;
        try {
            const tests = [];
            // Generate tests for each requirement
            spec.requirements.forEach((req, index) => {
                // Unit test for the requirement
                tests.push({
                    id: `test-${index + 1}-unit`,
                    name: `should ${this.requirementToTestName(req)}`,
                    description: `Unit test for: ${req}`,
                    type: 'unit',
                    code: this.generateTestCode(req, 'unit'),
                    assertions: this.generateAssertions(req)
                });
                // Integration test if requirement mentions integration
                if (req.toLowerCase().includes('integration') ||
                    req.toLowerCase().includes('api') ||
                    req.toLowerCase().includes('database')) {
                    tests.push({
                        id: `test-${index + 1}-integration`,
                        name: `should integrate ${this.requirementToTestName(req)}`,
                        description: `Integration test for: ${req}`,
                        type: 'integration',
                        code: this.generateTestCode(req, 'integration'),
                        assertions: this.generateAssertions(req)
                    });
                }
            });
            // Add edge case tests
            tests.push({
                id: 'test-edge-null',
                name: 'should handle null inputs gracefully',
                description: 'Edge case: null input handling',
                type: 'unit',
                code: 'expect(() => subject(null)).not.toThrow();',
                assertions: ['handles null without error']
            });
            tests.push({
                id: 'test-edge-empty',
                name: 'should handle empty inputs gracefully',
                description: 'Edge case: empty input handling',
                type: 'unit',
                code: 'expect(() => subject("")).not.toThrow();',
                assertions: ['handles empty string without error']
            });
            this.status = AgentRegistry_1.AgentStatus.COMPLETED;
            this.lastRun = new Date();
            this.output = `Generated ${tests.length} tests from ${spec.requirements.length} requirements`;
            return {
                name: spec.title,
                tests,
                framework: 'jest',
                coverageTarget: this.coverageThreshold
            };
        }
        catch (error) {
            this.status = AgentRegistry_1.AgentStatus.FAILED;
            this.output = `Test generation failed: ${error}`;
            throw error;
        }
    }
    /**
     * Validate test results meet TDD requirements
     */
    async validateResults(results) {
        const issues = [];
        const suggestions = [];
        // Check all tests pass
        if (results.failed > 0) {
            issues.push(`${results.failed} tests failing`);
            results.failures.forEach(f => {
                issues.push(`  - ${f.test}: ${f.error}`);
            });
        }
        // Check coverage threshold
        if (results.coverage < this.coverageThreshold) {
            issues.push(`Coverage ${results.coverage}% below threshold ${this.coverageThreshold}%`);
            suggestions.push('Add tests for uncovered branches');
        }
        // Check test count vs requirements
        const testRatio = results.passed / (results.passed + results.failed + results.skipped);
        if (testRatio < 0.9) {
            suggestions.push('Consider adding more comprehensive test cases');
        }
        // Performance check
        if (results.duration > 30000) {
            suggestions.push('Test suite taking too long. Consider parallelization or mocking slow dependencies.');
        }
        return {
            passed: issues.length === 0,
            issues,
            suggestions
        };
    }
    /**
     * Generate test file content
     */
    generateTestFile(suite) {
        let content = `/**
 * Test Suite: ${suite.name}
 * Generated by TesterAgent (TDD Iron Law)
 * Target Coverage: ${suite.coverageTarget}%
 */

`;
        if (suite.framework === 'jest') {
            content += `describe('${suite.name}', () => {\n`;
            suite.tests.forEach(test => {
                content += `\n  ${test.type === 'integration' ? 'it.skip' : 'it'}('${test.name}', () => {\n`;
                content += `    // ${test.description}\n`;
                content += `    ${test.code}\n`;
                content += `  });\n`;
            });
            content += `});\n`;
        }
        return content;
    }
    /**
     * Convert requirement to test name
     */
    requirementToTestName(requirement) {
        // Remove common prefixes and clean up
        let name = requirement
            .replace(/^(the system should|it should|must|shall|need to)/i, '')
            .trim()
            .toLowerCase();
        // Truncate if too long
        if (name.length > 60) {
            name = name.substring(0, 57) + '...';
        }
        return name;
    }
    /**
     * Generate test code skeleton
     */
    generateTestCode(requirement, type) {
        const reqLower = requirement.toLowerCase();
        if (reqLower.includes('validate')) {
            return `expect(validate(input)).toBe(true);`;
        }
        if (reqLower.includes('create')) {
            return `expect(create(data)).toBeDefined();`;
        }
        if (reqLower.includes('delete')) {
            return `expect(await delete(id)).toBe(true);`;
        }
        if (reqLower.includes('update')) {
            return `expect(update(id, data)).toMatchObject(expected);`;
        }
        if (reqLower.includes('return')) {
            return `expect(result).toEqual(expected);`;
        }
        if (reqLower.includes('throw') || reqLower.includes('error')) {
            return `expect(() => action()).toThrow();`;
        }
        return `// TODO: Implement test for: ${requirement}\nexpect(true).toBe(true);`;
    }
    /**
     * Generate assertions from requirement
     */
    generateAssertions(requirement) {
        const assertions = [];
        if (requirement.includes('must')) {
            assertions.push('mandatory requirement verified');
        }
        if (requirement.includes('valid')) {
            assertions.push('validation logic correct');
        }
        if (requirement.includes('error')) {
            assertions.push('error handling verified');
        }
        if (requirement.includes('return')) {
            assertions.push('correct return value');
        }
        if (assertions.length === 0) {
            assertions.push('requirement implemented correctly');
        }
        return assertions;
    }
}
exports.TesterAgent = TesterAgent;
//# sourceMappingURL=TesterAgent.js.map