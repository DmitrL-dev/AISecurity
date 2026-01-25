/**
 * Kiro Spec Reader
 * Reads .kiro/specs/ structure for SDD workflow status
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

/**
 * SDD Phase status
 */
export type SDDPhase = 'requirements' | 'design' | 'tasks' | 'implementation' | 'complete';

/**
 * Single specification status
 */
export interface SpecStatus {
    name: string;
    folderPath: string;
    workspaceRoot: string;
    phase: SDDPhase;
    hasRequirements: boolean;
    hasDesign: boolean;
    hasTasks: boolean;
    taskProgress?: { completed: number; total: number };
}

/**
 * Overall SDD status
 */
export interface SDDStatus {
    specs: SpecStatus[];
    currentPhase: SDDPhase;
    completedPhases: SDDPhase[];
    totalSpecs: number;
    completedSpecs: number;
}

/**
 * Kiro Spec Reader - scans .kiro/specs/ for SDD workflow data
 * Supports multi-root workspaces
 */
export class KiroSpecReader {
    private workspaceFolders: string[];

    constructor() {
        // Get all workspace folders
        this.workspaceFolders = vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) || [];
        
        // Fallback to cwd if no workspace
        if (this.workspaceFolders.length === 0) {
            this.workspaceFolders = [process.cwd()];
        }
    }

    /**
     * Get all .kiro/specs paths across workspace folders
     */
    private getKiroSpecsPaths(): Array<{ root: string; specsPath: string }> {
        const paths: Array<{ root: string; specsPath: string }> = [];
        
        for (const folder of this.workspaceFolders) {
            const specsPath = path.join(folder, '.kiro', 'specs');
            if (fs.existsSync(specsPath)) {
                paths.push({ root: folder, specsPath });
            }
        }
        
        return paths;
    }

    /**
     * Check if any .kiro/specs exists
     */
    hasKiroSpecs(): boolean {
        return this.getKiroSpecsPaths().length > 0;
    }

    /**
     * Get all specs from all workspace folders
     */
    async getSpecs(): Promise<SpecStatus[]> {
        const allSpecs: SpecStatus[] = [];
        const kiroPaths = this.getKiroSpecsPaths();
        
        if (kiroPaths.length === 0) {
            return [];
        }

        for (const { root, specsPath } of kiroPaths) {
            try {
                const entries = fs.readdirSync(specsPath, { withFileTypes: true });
                
                for (const entry of entries) {
                    if (entry.isDirectory()) {
                        const specPath = path.join(specsPath, entry.name);
                        const specStatus = await this.readSpecStatus(entry.name, specPath, root);
                        allSpecs.push(specStatus);
                    }
                }
            } catch (error) {
                console.error(`Error reading specs from ${specsPath}:`, error);
            }
        }

        return allSpecs;
    }

    /**
     * Read status of a single spec
     */
    private async readSpecStatus(name: string, specPath: string, workspaceRoot: string): Promise<SpecStatus> {
        const hasRequirements = fs.existsSync(path.join(specPath, 'requirements.md'));
        const hasDesign = fs.existsSync(path.join(specPath, 'design.md'));
        const hasTasks = fs.existsSync(path.join(specPath, 'tasks.md'));

        // Determine current phase
        let phase: SDDPhase = 'requirements';
        if (hasRequirements && !hasDesign) {
            phase = 'design';
        } else if (hasDesign && !hasTasks) {
            phase = 'tasks';
        } else if (hasTasks) {
            phase = 'implementation';
        }

        // Read task progress if tasks.md exists
        let taskProgress: { completed: number; total: number } | undefined;
        if (hasTasks) {
            taskProgress = await this.readTaskProgress(path.join(specPath, 'tasks.md'));
            if (taskProgress && taskProgress.completed === taskProgress.total && taskProgress.total > 0) {
                phase = 'complete';
            }
        }

        return {
            name,
            folderPath: specPath,
            workspaceRoot,
            phase,
            hasRequirements,
            hasDesign,
            hasTasks,
            taskProgress
        };
    }

    /**
     * Parse tasks.md to count completed vs total tasks
     */
    private async readTaskProgress(tasksPath: string): Promise<{ completed: number; total: number }> {
        try {
            const content = fs.readFileSync(tasksPath, 'utf-8');
            
            // Count checkboxes: [ ] = incomplete, [x] or [X] = complete
            const totalMatch = content.match(/\[[ xX\/]\]/g);
            const completedMatch = content.match(/\[[xX]\]/g);
            
            return {
                total: totalMatch?.length || 0,
                completed: completedMatch?.length || 0
            };
        } catch {
            return { completed: 0, total: 0 };
        }
    }

    /**
     * Get overall SDD status
     */
    async getSDDStatus(): Promise<SDDStatus> {
        const specs = await this.getSpecs();
        
        // Determine overall phase (most advanced phase among active specs)
        const phaseOrder: SDDPhase[] = ['requirements', 'design', 'tasks', 'implementation', 'complete'];
        let currentPhaseIndex = 0;
        const completedPhases: SDDPhase[] = [];

        for (const spec of specs) {
            const specPhaseIndex = phaseOrder.indexOf(spec.phase);
            if (specPhaseIndex > currentPhaseIndex) {
                currentPhaseIndex = specPhaseIndex;
            }
            
            // Track completed phases across all specs
            if (spec.hasRequirements && !completedPhases.includes('requirements')) {
                completedPhases.push('requirements');
            }
            if (spec.hasDesign && !completedPhases.includes('design')) {
                completedPhases.push('design');
            }
            if (spec.hasTasks && !completedPhases.includes('tasks')) {
                completedPhases.push('tasks');
            }
        }

        const completedSpecs = specs.filter(s => s.phase === 'complete').length;

        return {
            specs,
            currentPhase: phaseOrder[currentPhaseIndex],
            completedPhases,
            totalSpecs: specs.length,
            completedSpecs
        };
    }

    /**
     * Get status as JSON for webview
     */
    async getStatusForWebview(): Promise<{
        phase: string;
        completed: string[];
        specs: Array<{ name: string; phase: string; progress?: string }>;
    }> {
        const status = await this.getSDDStatus();
        
        return {
            phase: status.currentPhase,
            completed: status.completedPhases,
            specs: status.specs.map(s => ({
                name: s.name,
                phase: s.phase,
                progress: s.taskProgress 
                    ? `${s.taskProgress.completed}/${s.taskProgress.total}` 
                    : undefined
            }))
        };
    }
}
