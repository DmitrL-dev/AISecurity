"use strict";
/**
 * GitHub Integration Tests
 * TDD: Tests first
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
const GitHubIntegration_1 = require("../integrations/GitHubIntegration");
suite('GitHub Integration Test Suite', () => {
    test('Should create issue from QA review', async () => {
        const github = new GitHubIntegration_1.GitHubIntegration();
        const issue = await github.createIssueFromReview({
            id: '1',
            severity: 'high',
            description: 'Missing null check'
        });
        assert.ok(issue.number, 'Issue should have number');
        assert.ok(issue.title, 'Issue should have title');
        assert.ok(issue.labels.includes('devkit'), 'Should have devkit label');
    });
    test('Should create PR from implementation', async () => {
        const github = new GitHubIntegration_1.GitHubIntegration();
        const pr = await github.createPullRequest({
            title: 'feat: Add new feature',
            description: 'Implementation details',
            files: ['src/feature.ts'],
            branch: 'feat/new-feature'
        });
        assert.ok(pr.number, 'PR should have number');
        assert.ok(pr.url, 'PR should have URL');
    });
    test('Should link commit to task', async () => {
        const github = new GitHubIntegration_1.GitHubIntegration();
        const linked = await github.linkCommit('abc123', 'task-1');
        assert.ok(linked, 'Should successfully link');
    });
    test('Should get status checks', async () => {
        const github = new GitHubIntegration_1.GitHubIntegration();
        const checks = await github.getStatusChecks('main');
        assert.ok(Array.isArray(checks), 'Should return array');
    });
});
//# sourceMappingURL=github.test.js.map