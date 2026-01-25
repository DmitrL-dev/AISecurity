"use strict";
/**
 * Kiro Spec Reader
 * Reads .kiro/specs/ structure for SDD workflow status
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
exports.KiroSpecReader = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Kiro Spec Reader - scans .kiro/specs/ for SDD workflow data
 * Supports multi-root workspaces
 */
class KiroSpecReader {
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
    getKiroSpecsPaths() {
        const paths = [];
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
    hasKiroSpecs() {
        return this.getKiroSpecsPaths().length > 0;
    }
    /**
     * Get all specs from all workspace folders
     */
    async getSpecs() {
        const allSpecs = [];
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
            }
            catch (error) {
                console.error(`Error reading specs from ${specsPath}:`, error);
            }
        }
        return allSpecs;
    }
    /**
     * Read status of a single spec
     */
    async readSpecStatus(name, specPath, workspaceRoot) {
        const hasRequirements = fs.existsSync(path.join(specPath, 'requirements.md'));
        const hasDesign = fs.existsSync(path.join(specPath, 'design.md'));
        const hasTasks = fs.existsSync(path.join(specPath, 'tasks.md'));
        // Determine current phase
        let phase = 'requirements';
        if (hasRequirements && !hasDesign) {
            phase = 'design';
        }
        else if (hasDesign && !hasTasks) {
            phase = 'tasks';
        }
        else if (hasTasks) {
            phase = 'implementation';
        }
        // Read task progress if tasks.md exists
        let taskProgress;
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
    async readTaskProgress(tasksPath) {
        try {
            const content = fs.readFileSync(tasksPath, 'utf-8');
            // Count checkboxes: [ ] = incomplete, [x] or [X] = complete
            const totalMatch = content.match(/\[[ xX\/]\]/g);
            const completedMatch = content.match(/\[[xX]\]/g);
            return {
                total: totalMatch?.length || 0,
                completed: completedMatch?.length || 0
            };
        }
        catch {
            return { completed: 0, total: 0 };
        }
    }
    /**
     * Get overall SDD status
     */
    async getSDDStatus() {
        const specs = await this.getSpecs();
        // Determine overall phase (most advanced phase among active specs)
        const phaseOrder = ['requirements', 'design', 'tasks', 'implementation', 'complete'];
        let currentPhaseIndex = 0;
        const completedPhases = [];
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
    async getStatusForWebview() {
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
exports.KiroSpecReader = KiroSpecReader;
//# sourceMappingURL=KiroSpecReader.js.map