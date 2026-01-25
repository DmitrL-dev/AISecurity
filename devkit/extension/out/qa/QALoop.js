"use strict";
/**
 * QA Loop Engine
 * Manages Reviewer → Fixer cycle
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.QALoop = exports.QAStatus = void 0;
const AgentRegistry_1 = require("../agents/AgentRegistry");
/**
 * QA Loop status
 */
var QAStatus;
(function (QAStatus) {
    QAStatus["PENDING"] = "pending";
    QAStatus["IN_PROGRESS"] = "in_progress";
    QAStatus["APPROVED"] = "approved";
    QAStatus["REJECTED"] = "rejected";
    QAStatus["MAX_ITERATIONS_REACHED"] = "max_iterations";
})(QAStatus || (exports.QAStatus = QAStatus = {}));
/**
 * QA Loop - manages review/fix iterations
 */
class QALoop {
    constructor(maxIterations = 3) {
        this.currentIteration = 0;
        this.status = QAStatus.PENDING;
        this.issues = new Map();
        this.history = [];
        this.maxIterations = maxIterations;
        this.reviewer = new AgentRegistry_1.ReviewerAgent();
        this.fixer = new AgentRegistry_1.FixerAgent();
    }
    /**
     * Run one iteration of review/fix
     */
    async runIteration(input) {
        if (this.currentIteration >= this.maxIterations) {
            this.status = QAStatus.MAX_ITERATIONS_REACHED;
            return {
                review: { approved: false, stage1: { passed: false }, stage2: { passed: false }, issues: [] },
                fixed: 0
            };
        }
        this.currentIteration++;
        this.status = QAStatus.IN_PROGRESS;
        // Run review
        const review = await this.reviewer.review({ files: input.code.files, changes: input.code.changes || 0 }, input.spec);
        // Add new issues
        for (const issue of review.issues) {
            if (!this.issues.has(issue.id)) {
                this.issues.set(issue.id, {
                    ...issue,
                    fixed: false,
                    iteration: this.currentIteration
                });
            }
        }
        // Run fixer on open issues
        const openIssues = this.getOpenIssues();
        let fixed = 0;
        if (openIssues.length > 0) {
            const fixResult = await this.fixer.fix(openIssues);
            fixed = fixResult.fixed;
            // Mark as fixed (simplified - mark all open as fixed)
            for (const issue of openIssues.slice(0, fixed)) {
                this.markFixed(issue.id);
            }
        }
        // Record iteration
        this.history.push({
            iteration: this.currentIteration,
            timestamp: new Date(),
            review: {
                stage1Passed: review.stage1.passed,
                stage2Passed: review.stage2.passed,
                issuesFound: review.issues.length,
                issuesFixed: fixed
            },
            approved: review.approved
        });
        // Check if done
        if (this.currentIteration >= this.maxIterations && this.getOpenIssues().length > 0) {
            this.status = QAStatus.MAX_ITERATIONS_REACHED;
        }
        return { review, fixed };
    }
    /**
     * Add issue to tracking
     */
    addIssue(issue) {
        this.issues.set(issue.id, {
            ...issue,
            fixed: false,
            iteration: this.currentIteration
        });
    }
    /**
     * Mark issue as fixed
     */
    markFixed(id) {
        const issue = this.issues.get(id);
        if (issue) {
            issue.fixed = true;
            issue.fixedAt = new Date();
        }
    }
    /**
     * Get open (unfixed) issues
     */
    getOpenIssues() {
        return Array.from(this.issues.values()).filter(i => !i.fixed);
    }
    /**
     * Get fixed issues
     */
    getFixedIssues() {
        return Array.from(this.issues.values()).filter(i => i.fixed);
    }
    /**
     * Check if can complete (no open issues)
     */
    canComplete() {
        return this.getOpenIssues().length === 0;
    }
    /**
     * Approve the QA loop
     */
    async approve() {
        if (this.getOpenIssues().length === 0) {
            this.status = QAStatus.APPROVED;
            return true;
        }
        return false;
    }
    /**
     * Get iteration history
     */
    getHistory() {
        return [...this.history];
    }
    /**
     * Get summary stats
     */
    getSummary() {
        return {
            iterations: this.currentIteration,
            maxIterations: this.maxIterations,
            totalIssues: this.issues.size,
            fixedIssues: this.getFixedIssues().length,
            openIssues: this.getOpenIssues().length,
            status: this.status
        };
    }
}
exports.QALoop = QALoop;
//# sourceMappingURL=QALoop.js.map