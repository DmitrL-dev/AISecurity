/**
 * Tasks Reader
 * Parses tasks.md files from .kiro/specs/ into Kanban-compatible tasks
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export type TaskStatus = 'spec' | 'in-progress' | 'review' | 'done';

export interface KanbanTask {
    id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: 'low' | 'medium' | 'high';
    specName: string;
    phase?: string;
    subtasks?: number;
    filePath?: string;
    lineNumber?: number;
}

export interface KanbanData {
    tasks: KanbanTask[];
    specs: string[];
}

/**
 * Tasks Reader - parses tasks.md files from .kiro specs folders
 */
export class TasksReader {
    
    /**
     * Get workspace folders dynamically (not in constructor to avoid timing issues)
     */
    private getWorkspaceFolders(): string[] {
        const folders = vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) || [];
        if (folders.length === 0) {
            return [process.cwd()];
        }
        return folders;
    }

    /**
     * Get all kanban tasks from all specs
     */
    async getKanbanData(): Promise<KanbanData> {
        const allTasks: KanbanTask[] = [];
        const allSpecs: string[] = [];

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
    private parseTasksFile(filePath: string, specName: string): KanbanTask[] {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n');
        const tasks: KanbanTask[] = [];
        
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
                let status: TaskStatus;
                if (checkState === 'x' || checkState === 'X') {
                    status = 'done';
                } else if (checkState === '/') {
                    status = 'in-progress';
                } else {
                    status = 'spec';
                }

                // Extract task title and description
                const titleMatch = taskText.match(/\*\*(.+?)\*\*[:\s]*(.*)/);
                let title: string;
                let description: string | undefined;

                if (titleMatch) {
                    title = titleMatch[1];
                    description = titleMatch[2] || undefined;
                } else {
                    title = taskText;
                }

                // Determine priority based on phase or keywords
                let priority: 'low' | 'medium' | 'high' = 'medium';
                if (title.toLowerCase().includes('critical') || title.toLowerCase().includes('security')) {
                    priority = 'high';
                } else if (title.toLowerCase().includes('documentation') || title.toLowerCase().includes('docs')) {
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
    async getDataForWebview(): Promise<{
        columns: {
            spec: KanbanTask[];
            'in-progress': KanbanTask[];
            review: KanbanTask[];
            done: KanbanTask[];
        };
        specs: string[];
        totalTasks: number;
    }> {
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
