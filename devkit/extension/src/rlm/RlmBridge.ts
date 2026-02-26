/**
 * RLM Bridge
 * Connects to RLM-Toolkit Memory Bridge v2 SQLite database
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export interface RlmMemoryStatus {
    L0: number;      // Core facts count
    L1: number;      // Domain facts count
    L2: number;      // Module facts count
    L3: number;      // Code facts count
    total: number;   // Total facts
    domains: number; // Domain count
    available: boolean;
}

/**
 * RLM Bridge - reads from Memory Bridge v2 SQLite database
 */
export class RlmBridge {
    private workspaceRoot: string;

    constructor() {
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    }

    /**
     * Get RLM memory statistics from SQLite database
     */
    async getStatus(): Promise<RlmMemoryStatus> {
        const rlmDbPath = path.join(this.workspaceRoot, '.rlm', 'memory', 'memory_bridge_v2.db');
        
        // Check if database exists
        if (!fs.existsSync(rlmDbPath)) {
            return {
                L0: 0,
                L1: 0,
                L2: 0,
                L3: 0,
                total: 0,
                domains: 0,
                available: false
            };
        }

        try {
            // Use better-sqlite3 if available, otherwise fall back to file inspection
            const stats = await this.readSqliteStats(rlmDbPath);
            return {
                ...stats,
                available: true
            };
        } catch (error) {
            console.log('RLM Bridge: Error reading SQLite database:', error);
            // Fall back to counting files
            return this.getFallbackStats();
        }
    }

    /**
     * Read stats from SQLite database using shell command
     * Since VS Code extension can't easily use native modules,
     * we shell out to sqlite3 CLI if available
     */
    private async readSqliteStats(dbPath: string): Promise<{L0: number; L1: number; L2: number; L3: number; total: number; domains: number}> {
        const { exec } = await import('child_process');
        const { promisify } = await import('util');
        const execAsync = promisify(exec);

        try {
            // Try using Python to read SQLite (more reliable on Windows)
            const pythonScript = `
import sqlite3
import json
import sys

db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count facts by level
counts = {'L0': 0, 'L1': 0, 'L2': 0, 'L3': 0, 'total': 0, 'domains': 0}

# Check if hierarchical_facts table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hierarchical_facts'")
if cursor.fetchone():
    cursor.execute("SELECT level, COUNT(*) FROM hierarchical_facts WHERE archived = 0 GROUP BY level")
    for row in cursor.fetchall():
        level = row[0]
        count = row[1]
        if level == 0:
            counts['L0'] = count
        elif level == 1:
            counts['L1'] = count
        elif level == 2:
            counts['L2'] = count
        elif level == 3:
            counts['L3'] = count
    
    cursor.execute("SELECT COUNT(*) FROM hierarchical_facts WHERE archived = 0")
    counts['total'] = cursor.fetchone()[0]
    
    # Count unique domains
    cursor.execute("SELECT COUNT(DISTINCT domain) FROM hierarchical_facts WHERE domain IS NOT NULL AND archived = 0")
    counts['domains'] = cursor.fetchone()[0]

conn.close()
print(json.dumps(counts))
`;
            const escapedPath = dbPath.replace(/\\/g, '\\\\');
            const { stdout } = await execAsync(
                `python -c "${pythonScript.replace(/"/g, '\\"').replace(/\n/g, '\\n')}" "${escapedPath}"`,
                { timeout: 5000 }
            );
            
            const result = JSON.parse(stdout.trim());
            return result;
        } catch (pythonError) {
            // Fallback: Try sqlite3 CLI directly
            try {
                const query = `
                    SELECT 
                        SUM(CASE WHEN level = 0 THEN 1 ELSE 0 END) as L0,
                        SUM(CASE WHEN level = 1 THEN 1 ELSE 0 END) as L1,
                        SUM(CASE WHEN level = 2 THEN 1 ELSE 0 END) as L2,
                        SUM(CASE WHEN level = 3 THEN 1 ELSE 0 END) as L3,
                        COUNT(*) as total
                    FROM hierarchical_facts WHERE archived = 0;
                `;
                const { stdout } = await execAsync(
                    `sqlite3 "${dbPath}" "${query}"`,
                    { timeout: 5000 }
                );
                
                const parts = stdout.trim().split('|');
                return {
                    L0: parseInt(parts[0]) || 0,
                    L1: parseInt(parts[1]) || 0,
                    L2: parseInt(parts[2]) || 0,
                    L3: parseInt(parts[3]) || 0,
                    total: parseInt(parts[4]) || 0,
                    domains: 0
                };
            } catch (sqliteError) {
                throw sqliteError;
            }
        }
    }

    /**
     * Fallback: estimate stats from RLM directory structure
     */
    private getFallbackStats(): RlmMemoryStatus {
        const rlmPath = path.join(this.workspaceRoot, '.rlm');
        
        if (!fs.existsSync(rlmPath)) {
            return { L0: 0, L1: 0, L2: 0, L3: 0, total: 0, domains: 0, available: false };
        }

        try {
            // Check for state.json
            const stateFile = path.join(rlmPath, 'sessions', 'default', 'state.json');
            if (fs.existsSync(stateFile)) {
                const state = JSON.parse(fs.readFileSync(stateFile, 'utf-8'));
                if (state.facts) {
                    const L0 = state.facts.L0 || 0;
                    const L1 = state.facts.L1 || 0;
                    const L2 = state.facts.L2 || 0;
                    const L3 = state.facts.L3 || 0;
                    return {
                        L0, L1, L2, L3,
                        total: L0 + L1 + L2 + L3,
                        domains: state.domains?.length || 0,
                        available: true
                    };
                }
            }

            // Estimate from database file size
            const dbPath = path.join(rlmPath, 'memory', 'memory_bridge_v2.db');
            if (fs.existsSync(dbPath)) {
                const stats = fs.statSync(dbPath);
                // Rough estimate: ~500 bytes per fact on average
                const estimatedFacts = Math.floor(stats.size / 500);
                return {
                    L0: Math.floor(estimatedFacts * 0.05),
                    L1: Math.floor(estimatedFacts * 0.15),
                    L2: Math.floor(estimatedFacts * 0.40),
                    L3: Math.floor(estimatedFacts * 0.40),
                    total: estimatedFacts,
                    domains: Math.floor(estimatedFacts / 10),
                    available: true
                };
            }

            return { L0: 0, L1: 0, L2: 0, L3: 0, total: 0, domains: 0, available: false };
        } catch (error) {
            console.log('RLM Bridge: Fallback stats error:', error);
            return { L0: 0, L1: 0, L2: 0, L3: 0, total: 0, domains: 0, available: false };
        }
    }

    /**
     * Get status for webview
     */
    async getStatusForWebview(): Promise<{
        L0: number;
        L1: number;
        L2: number;
        L3: number;
        total: number;
        domains: number;
        available: boolean;
    }> {
        return this.getStatus();
    }
}
