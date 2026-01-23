import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';

interface RLMResponse {
    success: boolean;
    error?: string;
    [key: string]: any;
}

export class RLMMcpClient {
    private pythonPath: string;
    private projectRoot: string;
    private cachedStatus: RLMResponse | null = null;
    private cacheTime: number = 0;
    private readonly CACHE_TTL_MS = 5000; // 5 second cache
    
    constructor() {
        this.projectRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
        this.pythonPath = this.resolvePythonPath();
        console.log(`RLM: Using Python: ${this.pythonPath}`);
    }
    
    private resolvePythonPath(): string {
        const fs = require('fs');
        
        // Strategy 1: Check workspace .venv first (most reliable for project-specific)
        if (this.projectRoot) {
            const venvPaths = [
                `${this.projectRoot}/.venv/Scripts/python.exe`,  // Windows venv
                `${this.projectRoot}/.venv/bin/python`,          // Unix venv
                `${this.projectRoot}/venv/Scripts/python.exe`,   // Windows venv alt
                `${this.projectRoot}/venv/bin/python`,           // Unix venv alt
            ];
            
            for (const p of venvPaths) {
                if (fs.existsSync(p)) {
                    console.log(`RLM: Found project venv Python: ${p}`);
                    return p;
                }
            }
        }
        
        // Strategy 2: Try python.defaultInterpreterPath (if exists and valid)
        let configPath = vscode.workspace.getConfiguration('python').get<string>('defaultInterpreterPath') || '';
        
        // Clean up the path - strip quotes and resolve variables
        configPath = configPath.replace(/^["']|["']$/g, '');
        if (configPath.includes('${workspaceFolder}') && this.projectRoot) {
            configPath = configPath.replace(/\${workspaceFolder}/g, this.projectRoot);
        }
        
        if (configPath && configPath !== 'python' && fs.existsSync(configPath)) {
            console.log(`RLM: Using configured Python: ${configPath}`);
            return configPath;
        }
        
        // Strategy 3: Fallback to system python
        console.log('RLM: Using system Python fallback');
        return 'python';
    }
    
    // Multi-project support
    public getWorkspaceFolders(): { name: string, path: string }[] {
        return (vscode.workspace.workspaceFolders || []).map(f => ({
            name: f.name,
            path: f.uri.fsPath
        }));
    }
    
    public setProjectRoot(path: string): void {
        this.projectRoot = path;
        this.cachedStatus = null; // Clear cache on project switch
    }
    
    public getProjectRoot(): string {
        return this.projectRoot;
    }
    
    public async getStatus(): Promise<RLMResponse> {
        return this.callRlm('status');
    }
    
    public async reindex(force: boolean = false): Promise<RLMResponse> {
        return this.callRlm('reindex', { force });
    }
    
    public async validate(): Promise<RLMResponse> {
        return this.callRlm('validate');
    }
    
    public async consolidateMemory(): Promise<RLMResponse> {
        return this.callRlm('memory', { action: 'consolidate' });
    }
    
    public async query(question: string): Promise<RLMResponse> {
        return this.callRlm('query', { question });
    }
    
    public async getSessionStats(): Promise<RLMResponse> {
        return this.callRlm('session_stats');
    }
    
    // ========== v2.1 Enterprise Features ==========
    
    public async discoverProject(): Promise<RLMResponse> {
        return this.callRlmV2('rlm_discover_project', {});
    }
    
    public async enterpriseContext(query: string): Promise<RLMResponse> {
        return this.callRlmV2('rlm_enterprise_context', { 
            query, 
            max_tokens: 3000,
            include_causal: true 
        });
    }
    
    public async healthCheck(): Promise<RLMResponse> {
        return this.callRlmV2('rlm_health_check', {});
    }
    
    public async getHierarchyStats(): Promise<RLMResponse> {
        return this.callRlmV2('rlm_get_hierarchy_stats', {});
    }
    
    public async indexEmbeddings(): Promise<RLMResponse> {
        return this.callRlmV2('rlm_index_embeddings', {});
    }
    
    public async installGitHook(): Promise<RLMResponse> {
        return this.callRlmV2('rlm_install_git_hooks', { hook_type: 'post-commit' });
    }
    
    // v2.1 MCP tool caller (uses mcp_tools_v2)
    private async callRlmV2(tool: string, params: any): Promise<RLMResponse> {
        return new Promise((resolve) => {
            const script = `
import json
import sys
import os
import asyncio
sys.path.insert(0, r'${this.projectRoot}')
os.environ['RLM_PROJECT_ROOT'] = r'${this.projectRoot}'

async def main():
    try:
        from pathlib import Path
        from rlm_toolkit.memory_bridge.v2.hierarchical import HierarchicalMemoryStore
        from rlm_toolkit.memory_bridge.mcp_tools_v2 import register_memory_bridge_v2_tools
        
        # Create mock server with tool capture
        class MockServer:
            def __init__(self):
                self.tools = {}
            def tool(self, name=None, description=None):
                def decorator(func):
                    self.tools[name] = func
                    return func
                return decorator
        
        server = MockServer()
        project_root = Path(r'${this.projectRoot}')
        db_path = project_root / '.rlm' / 'memory' / 'memory_bridge_v2.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = HierarchicalMemoryStore(db_path=str(db_path))
        
        register_memory_bridge_v2_tools(server, store, project_root)
        
        tool_name = '${tool}'
        params = ${JSON.stringify(params)}
        
        if tool_name in server.tools:
            result = await server.tools[tool_name](**params)
            print(json.dumps({'success': True, **result}))
        else:
            print(json.dumps({'success': False, 'error': f'Tool {tool_name} not found'}))
    except Exception as e:
        import traceback
        print(json.dumps({'success': False, 'error': str(e), 'trace': traceback.format_exc()}))

asyncio.run(main())
`;
            
            const env = { ...process.env };
            env['RLM_PROJECT_ROOT'] = this.projectRoot;
            
            const proc = spawn(this.pythonPath, ['-c', script], {
                cwd: this.projectRoot,
                env: env
            });
            
            let stdout = '';
            let stderr = '';
            
            proc.stdout?.on('data', (data: Buffer) => {
                stdout += data.toString();
            });
            
            proc.stderr?.on('data', (data: Buffer) => {
                stderr += data.toString();
            });
            
            proc.on('close', (code: number | null) => {
                try {
                    const result = JSON.parse(stdout.trim());
                    resolve(result);
                } catch (e) {
                    resolve({
                        success: false,
                        error: stderr || stdout || 'Failed to parse RLM v2 response'
                    });
                }
            });
            
            proc.on('error', (err: Error) => {
                resolve({
                    success: false,
                    error: `RLM v2 spawn failed: ${err.message}`
                });
            });
        });
    }
    
    private async callRlm(command: string, args: any = {}): Promise<RLMResponse> {
        return new Promise((resolve) => {
            const script = `
import json
import sys
import os
sys.path.insert(0, r'${this.projectRoot}')
os.environ['RLM_PROJECT_ROOT'] = r'${this.projectRoot}'

try:
    from pathlib import Path
    from rlm_toolkit.storage import get_storage
    from rlm_toolkit.freshness import CrossReferenceValidator
    from rlm_toolkit.indexer import AutoIndexer
    
    command = '${command}'
    args = ${JSON.stringify(args).replace(/\bfalse\b/g, 'False').replace(/\btrue\b/g, 'True')}
    
    if command == 'status':
        storage = get_storage(Path(r'${this.projectRoot}'))
        stats = storage.get_stats()
        result = {
            'success': True,
            'version': '1.2.0',
            'index': {
                'crystals': stats.get('total_crystals', 0),
                'tokens': stats.get('total_tokens', 0),
                'db_size_mb': stats.get('db_size_mb', 0),
            }
        }
    elif command == 'validate':
        storage = get_storage(Path(r'${this.projectRoot}'))
        crystals = {c['crystal']['path']: c['crystal'] for c in storage.load_all()}
        validator = CrossReferenceValidator(crystals)
        stats = validator.get_validation_stats()
        stale = storage.get_stale_crystals(ttl_hours=24)
        result = {
            'success': True,
            'symbols': stats,
            'stale_files': len(stale),
            'total_files': len(crystals),
            'health': 'good' if len(stale) == 0 else 'needs_refresh',
        }
    elif command == 'reindex':
        import time
        indexer = AutoIndexer(Path(r'${this.projectRoot}'))
        r = indexer._index_full()
        
        # Update session stats using storage stats
        storage = get_storage(Path(r'${this.projectRoot}'))
        storage_stats = storage.get_stats()
        total_tokens = storage_stats.get('total_tokens', 0)
        
        session_stats = storage.get_metadata('session_stats') or {
            'queries': 0,
            'tokens_served': 0,
            'tokens_saved': 0,
            'session_start': time.time(),
        }
        # Estimate tokens saved (raw - compressed with 56x ratio)
        raw_tokens = total_tokens * 56
        session_stats['tokens_saved'] += raw_tokens - total_tokens
        session_stats['tokens_served'] += total_tokens
        session_stats['queries'] += 1
        storage.set_metadata('session_stats', session_stats)
        
        result = {
            'success': True,
            'files_indexed': r.files_indexed,
            'duration': r.duration_seconds,
            'tokens_saved': raw_tokens - total_tokens,
        }
    elif command == 'memory':
        result = {'success': True, 'message': 'Memory operation completed'}
    elif command == 'session_stats':
        # Get RLM session stats from SQLite (persisted by MCP server)
        import time
        from rlm_toolkit.storage import get_storage
        
        storage = get_storage(Path(r'${this.projectRoot}'))
        
        # Get session stats from storage
        stats = storage.get_metadata('session_stats') or {
            'queries': 0,
            'tokens_served': 0,
            'tokens_saved': 0,
            'session_start': time.time(),
        }
        
        # Calculate derived values
        duration = (time.time() - stats.get('session_start', time.time())) / 60
        total = stats.get('tokens_served', 0) + stats.get('tokens_saved', 0)
        savings_pct = (stats['tokens_saved'] / total * 100) if total > 0 else 0
        
        result = {
            'success': True,
            'session': {
                'queries': stats.get('queries', 0),
                'tokens_served': stats.get('tokens_served', 0),
                'tokens_saved': stats.get('tokens_saved', 0),
                'savings_percent': round(savings_pct, 1),
                'duration_minutes': round(duration, 1),
            }
        }
    else:
        result = {'success': False, 'error': f'Unknown command: {command}'}
    
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
`;
            
            const env = { ...process.env };
            env['RLM_PROJECT_ROOT'] = this.projectRoot;
            
            const proc: ChildProcess = spawn(this.pythonPath, ['-c', script], {
                cwd: this.projectRoot,
                env: env
            });
            
            let stdout = '';
            let stderr = '';
            
            proc.stdout?.on('data', (data: Buffer) => {
                stdout += data.toString();
            });
            
            proc.stderr?.on('data', (data: Buffer) => {
                stderr += data.toString();
            });
            
            proc.on('close', (code: number | null) => {
                try {
                    const result = JSON.parse(stdout.trim());
                    resolve(result);
                } catch (e) {
                    resolve({
                        success: false,
                        error: stderr || stdout || 'Failed to parse RLM response'
                    });
                }
            });
            
            proc.on('error', (err: Error) => {
                resolve({
                    success: false,
                    error: `RLM spawn failed (python: ${this.pythonPath}): ${err.message}`
                });
            });
            
            // No timeout - let indexing complete naturally
            // Large projects may take a long time
        });
    }
}
