"use strict";
/**
 * Tasks Reader
 * Parses tasks.md files from .kiro/specs/ into Kanban-compatible tasks
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
exports.TasksReader = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Tasks Reader - parses tasks.md files from .kiro specs folders
 */
class TasksReader {
    /**
     * Get workspace folders dynamically (not in constructor to avoid timing issues)
     */
    getWorkspaceFolders() {
        const folders = vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) || [];
        if (folders.length === 0) {
            return [process.cwd()];
        }
        return folders;
    }
    /**
     * Get all kanban tasks from all specs
     */
    async getKanbanData() {
        const allTasks = [];
        const allSpecs = [];
        for (const folder of this.getWorkspaceFolders()) {
            const specsPath = path.join(folder, '.kiro', 'specs');
            if (!fs.existsSync(specsPath)) {
                continue;
            }
            const entries = fs.readdirSync(specsPath, { withFileTypes: true });
            for (const entry of entries) {
                if (entry.isDirectory()) {
                    const specName = entry.name;
                    allSpecs.push(specName);
                    const tasksFile = path.join(specsPath, specName, 'tasks.md');
                    if (fs.existsSync(tasksFile)) {
                        const tasks = this.parseTasksFile(tasksFile, specName);
                        allTasks.push(...tasks);
                    }
                }
            }
        }
        return { tasks: allTasks, specs: allSpecs };
    }
    /**
     * Parse a tasks.md file into KanbanTask array
     */
    parseTasksFile(filePath, specName) {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n');
        const tasks = [];
        let currentPhase = '';
        let taskIndex = 0;
        let lineNumber = 0;
        for (const line of lines) {
            lineNumber++;
            // Detect phase headers (## Phase X: ...)
            const phaseMatch = line.match(/^##\s+(?:Phase\s+\d+[:.]\s*)?(.+)/);
            if (phaseMatch) {
                currentPhase = phaseMatch[1].replace(/[🔄⏳✅📖🔧🧪🏆]/g, '').trim();
            }
            // Parse checkbox lines
            const taskMatch = line.match(/^[\s-]*\[([ xX\/])\]\s+(.+)/);
            if (taskMatch) {
                const checkState = taskMatch[1];
                const taskText = taskMatch[2];
                // Determine status from checkbox
                let status;
                if (checkState === 'x' || checkState === 'X') {
                    status = 'done';
                }
                else if (checkState === '/') {
                    status = 'in-progress';
                }
                else {
                    status = 'spec';
                }
                // Extract task title and description
                const titleMatch = taskText.match(/\*\*(.+?)\*\*[:\s]*(.*)/);
                let title;
                let description;
                if (titleMatch) {
                    title = titleMatch[1];
                    description = titleMatch[2] || undefined;
                }
                else {
                    title = taskText;
                }
                // Determine priority based on phase or keywords
                let priority = 'medium';
                if (title.toLowerCase().includes('critical') || title.toLowerCase().includes('security')) {
                    priority = 'high';
                }
                else if (title.toLowerCase().includes('documentation') || title.toLowerCase().includes('docs')) {
                    priority = 'low';
                }
                tasks.push({
                    id: `${specName}-${taskIndex++}`,
                    title: title.substring(0, 50) + (title.length > 50 ? '...' : ''),
                    description,
                    status,
                    priority,
                    specName,
                    phase: currentPhase || undefined,
                    filePath: filePath,
                    lineNumber: lineNumber
                });
            }
        }
        return tasks;
    }
    /**
     * Get kanban data formatted for webview
     */
    async getDataForWebview() {
        const data = await this.getKanbanData();
        const columns = {
            spec: data.tasks.filter(t => t.status === 'spec'),
            'in-progress': data.tasks.filter(t => t.status === 'in-progress'),
            review: data.tasks.filter(t => t.status === 'review'),
            done: data.tasks.filter(t => t.status === 'done')
        };
        return {
            columns,
            specs: data.specs,
            totalTasks: data.tasks.length
        };
    }
}
exports.TasksReader = TasksReader;
//# sourceMappingURL=TasksReader.js.map