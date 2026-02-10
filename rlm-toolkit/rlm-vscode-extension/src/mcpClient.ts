import * as vscode from "vscode";
import { spawn, ChildProcess } from "child_process";
import * as path from "path";

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
    this.projectRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || "";
    this.pythonPath = this.resolvePythonPath();
    console.log(`RLM: Using Python: ${this.pythonPath}`);
  }

  private resolvePythonPath(): string {
    const fs = require("fs");

    // Strategy 1: Check workspace .venv first (most reliable for project-specific)
    if (this.projectRoot) {
      const venvPaths = [
        `${this.projectRoot}/.venv/Scripts/python.exe`, // Windows venv
        `${this.projectRoot}/.venv/bin/python`, // Unix venv
        `${this.projectRoot}/venv/Scripts/python.exe`, // Windows venv alt
        `${this.projectRoot}/venv/bin/python`, // Unix venv alt
      ];

      for (const p of venvPaths) {
        if (fs.existsSync(p)) {
          console.log(`RLM: Found project venv Python: ${p}`);
          return p;
        }
      }
    }

    // Strategy 2: Try python.defaultInterpreterPath (if exists and valid)
    let configPath =
      vscode.workspace
        .getConfiguration("python")
        .get<string>("defaultInterpreterPath") || "";

    // Clean up the path - strip quotes and resolve variables
    configPath = configPath.replace(/^["']|["']$/g, "");
    if (configPath.includes("${workspaceFolder}") && this.projectRoot) {
      configPath = configPath.replace(/\${workspaceFolder}/g, this.projectRoot);
    }

    if (configPath && configPath !== "python" && fs.existsSync(configPath)) {
      console.log(`RLM: Using configured Python: ${configPath}`);
      return configPath;
    }

    // Strategy 3: Fallback to system python
    console.log("RLM: Using system Python fallback");
    return "python";
  }

  // Multi-project support
  public getWorkspaceFolders(): { name: string; path: string }[] {
    return (vscode.workspace.workspaceFolders || []).map((f) => ({
      name: f.name,
      path: f.uri.fsPath,
    }));
  }

  public setProjectRoot(path: string): void {
    this.projectRoot = path;
    this.cachedStatus = null; // Clear cache on project switch
  }

  public getProjectRoot(): string {
    return this.projectRoot;
  }

  // ========== All tools — unified v2 path ==========

  public async getStatus(): Promise<RLMResponse> {
    return this.callTool("rlm_status", {});
  }

  public async reindex(force: boolean = false): Promise<RLMResponse> {
    return this.callTool("rlm_reindex", { force });
  }

  public async validate(): Promise<RLMResponse> {
    return this.callTool("rlm_validate", {});
  }

  public async consolidateMemory(): Promise<RLMResponse> {
    return this.callTool("rlm_consolidate_facts", { min_facts: 5 });
  }

  public async getSessionStats(): Promise<RLMResponse> {
    return this.callTool("rlm_session_stats", {});
  }

  public async discoverProject(): Promise<RLMResponse> {
    return this.callTool("rlm_discover_project", {});
  }

  public async enterpriseContext(query: string): Promise<RLMResponse> {
    return this.callTool("rlm_enterprise_context", {
      query,
      max_tokens: 3000,
      include_causal: true,
    });
  }

  public async healthCheck(): Promise<RLMResponse> {
    return this.callTool("rlm_health_check", {});
  }

  public async getHierarchyStats(): Promise<RLMResponse> {
    return this.callTool("rlm_get_hierarchy_stats", {});
  }

  public async indexEmbeddings(): Promise<RLMResponse> {
    return this.callTool("rlm_index_embeddings", {});
  }

  public async installGitHook(): Promise<RLMResponse> {
    return this.callTool("rlm_install_git_hooks", { hook_type: "post-commit" });
  }

  // ========== Unified tool executor ==========

  private async callTool(tool: string, params: any): Promise<RLMResponse> {
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
            # Normalize: v2 tools return status='success', extension expects success=True
            if isinstance(result, dict):
                result['success'] = result.get('status') == 'success'
            print(json.dumps(result))
        else:
            available = sorted(server.tools.keys())
            print(json.dumps({
                'success': False,
                'error': f'Tool {tool_name} not found. Available: {available}'
            }))
    except Exception as e:
        import traceback
        print(json.dumps({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }))

asyncio.run(main())
`;

      const env = { ...process.env };
      env["RLM_PROJECT_ROOT"] = this.projectRoot;

      const proc = spawn(this.pythonPath, ["-c", script], {
        cwd: this.projectRoot,
        env: env,
      });

      let stdout = "";
      let stderr = "";

      proc.stdout?.on("data", (data: Buffer) => {
        stdout += data.toString();
      });

      proc.stderr?.on("data", (data: Buffer) => {
        stderr += data.toString();
      });

      proc.on("close", (code: number | null) => {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch (e) {
          resolve({
            success: false,
            error: stderr || stdout || "Failed to parse RLM response",
          });
        }
      });

      proc.on("error", (err: Error) => {
        resolve({
          success: false,
          error: `RLM spawn failed (python: ${this.pythonPath}): ${err.message}`,
        });
      });

      // No timeout - let indexing complete naturally
      // Large projects may take a long time
    });
  }
}
