/**
 * GitHub Integration Tests
 * TDD: Tests first
 */

import * as assert from 'assert';
import { GitHubIntegration, GitHubIssue, PullRequest } from '../integrations/GitHubIntegration';

suite('GitHub Integration Test Suite', () => {

    test('Should create issue from QA review', async () => {
        const github = new GitHubIntegration();
        
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
        const github = new GitHubIntegration();
        
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
        const github = new GitHubIntegration();
        
        const linked = await github.linkCommit('abc123', 'task-1');
        
        assert.ok(linked, 'Should successfully link');
    });

    test('Should get status checks', async () => {
        const github = new GitHubIntegration();
        
        const checks = await github.getStatusChecks('main');
        
        assert.ok(Array.isArray(checks), 'Should return array');
    });
});
