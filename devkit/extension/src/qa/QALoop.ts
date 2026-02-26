/**
 * QA Loop Engine
 * Manages Reviewer → Fixer cycle
 */

import { ReviewerAgent, FixerAgent, ReviewIssue, Spec } from '../agents/AgentRegistry';

/**
 * QA Loop status
 */
export enum QAStatus {
    PENDING = 'pending',
    IN_PROGRESS = 'in_progress',
    APPROVED = 'approved',
    REJECTED = 'rejected',
    MAX_ITERATIONS_REACHED = 'max_iterations'
}

/**
 * Issue with tracking
 */
export interface TrackedIssue extends ReviewIssue {
    fixed: boolean;
    fixedAt?: Date;
    iteration: number;
}

/**
 * QA Iteration record
 */
export interface QAIteration {
    iteration: number;
    timestamp: Date;
    review: {
        stage1Passed: boolean;
        stage2Passed: boolean;
        issuesFound: number;
        issuesFixed: number;
    };
    approved: boolean;
}

/**
 * Code input for review
 */
interface CodeInput {
    files: string[];
    changes?: number;
}

/**
 * Iteration input
 */
interface IterationInput {
    code: CodeInput;
    spec: Spec;
}

/**
 * Iteration result
 */
interface IterationResult {
    review: {
        approved: boolean;
        stage1: { passed: boolean };
        stage2: { passed: boolean };
        issues: ReviewIssue[];
    };
    fixed: number;
}

/**
 * QA Loop - manages review/fix iterations
 */
export class QALoop {
    readonly maxIterations: number;
    currentIteration: number = 0;
    status: QAStatus = QAStatus.PENDING;

    private issues: Map<string, TrackedIssue> = new Map();
    private history: QAIteration[] = [];
    private reviewer: ReviewerAgent;
    private fixer: FixerAgent;

    constructor(maxIterations: number = 3) {
        this.maxIterations = maxIterations;
        this.reviewer = new ReviewerAgent();
        this.fixer = new FixerAgent();
    }

    /**
     * Run one iteration of review/fix
     */
    async runIteration(input: IterationInput): Promise<IterationResult> {
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
        const review = await this.reviewer.review(
            { files: input.code.files, changes: input.code.changes || 0 },
            input.spec
        );

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
    addIssue(issue: ReviewIssue): void {
        this.issues.set(issue.id, {
            ...issue,
            fixed: false,
            iteration: this.currentIteration
        });
    }

    /**
     * Mark issue as fixed
     */
    markFixed(id: string): void {
        const issue = this.issues.get(id);
        if (issue) {
            issue.fixed = true;
            issue.fixedAt = new Date();
        }
    }

    /**
     * Get open (unfixed) issues
     */
    getOpenIssues(): TrackedIssue[] {
        return Array.from(this.issues.values()).filter(i => !i.fixed);
    }

    /**
     * Get fixed issues
     */
    getFixedIssues(): TrackedIssue[] {
        return Array.from(this.issues.values()).filter(i => i.fixed);
    }

    /**
     * Check if can complete (no open issues)
     */
    canComplete(): boolean {
        return this.getOpenIssues().length === 0;
    }

    /**
     * Approve the QA loop
     */
    async approve(): Promise<boolean> {
        if (this.getOpenIssues().length === 0) {
            this.status = QAStatus.APPROVED;
            return true;
        }
        return false;
    }

    /**
     * Get iteration history
     */
    getHistory(): QAIteration[] {
        return [...this.history];
    }

    /**
     * Get summary stats
     */
    getSummary(): {
        iterations: number;
        maxIterations: number;
        totalIssues: number;
        fixedIssues: number;
        openIssues: number;
        status: QAStatus;
    } {
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
