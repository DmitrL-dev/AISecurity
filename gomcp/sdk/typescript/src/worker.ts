/**
 * Worker for stdio-based MCP communication
 */

import { createInterface } from 'node:readline';
import type { JsonRpcRequest, JsonRpcResponse, ToolResult, WorkerConfig, ToolMetadata } from './types.js';
import { ErrorCode } from './types.js';
import { getRegisteredTools, getTool } from './decorators.js';

/**
 * Worker class for handling MCP protocol over stdio
 */
export class Worker {
  private readonly config: WorkerConfig;
  private running = false;

  constructor(config: WorkerConfig = {}) {
    this.config = {
      name: config.name ?? 'gomcp-ts-worker',
      defaultTimeoutMs: config.defaultTimeoutMs ?? 30000,
    };
  }

  /**
   * Get all registered tool definitions
   */
  getToolDefinitions(): Array<{ name: string; description: string; inputSchema: Record<string, unknown> }> {
    const tools = getRegisteredTools();
    return Array.from(tools.values()).map(t => ({
      name: t.definition.name,
      description: t.definition.description,
      inputSchema: t.definition.inputSchema,
    }));
  }

  /**
   * Call a tool by name with given arguments
   */
  async callTool(name: string, args: unknown): Promise<ToolResult> {
    const tool = getTool(name);
    
    if (!tool) {
      return {
        error: {
          code: ErrorCode.ToolNotFound,
          message: `Tool not found: ${name}`,
        },
      };
    }

    const start = Date.now();
    const result = await tool.handler(args);
    result.durationMs = Date.now() - start;
    
    return result;
  }

  /**
   * Handle a JSON-RPC request
   */
  async handleRequest(request: JsonRpcRequest): Promise<JsonRpcResponse> {
    const { id, method, params } = request;

    try {
      switch (method) {
        case 'tools/list':
          return {
            jsonrpc: '2.0',
            id,
            result: {
              tools: this.getToolDefinitions(),
            },
          };

        case 'tools/call': {
          const { name, arguments: args } = params as { name: string; arguments?: unknown };
          const result = await this.callTool(name, args ?? {});
          
          if (result.error) {
            return {
              jsonrpc: '2.0',
              id,
              error: {
                code: result.error.code,
                message: result.error.message,
                data: result.error.details,
              },
            };
          }
          
          return {
            jsonrpc: '2.0',
            id,
            result: {
              content: [
                {
                  type: 'text',
                  text: typeof result.output === 'string' 
                    ? result.output 
                    : JSON.stringify(result.output),
                },
              ],
            },
          };
        }

        case 'initialize':
          return {
            jsonrpc: '2.0',
            id,
            result: {
              protocolVersion: '1.0',
              capabilities: {
                tools: {},
              },
              serverInfo: {
                name: this.config.name,
                version: '1.0.0',
              },
            },
          };

        case 'ping':
          return {
            jsonrpc: '2.0',
            id,
            result: { pong: true },
          };

        default:
          return {
            jsonrpc: '2.0',
            id,
            error: {
              code: -32601,
              message: `Method not found: ${method}`,
            },
          };
      }
    } catch (error) {
      return {
        jsonrpc: '2.0',
        id,
        error: {
          code: -32603,
          message: error instanceof Error ? error.message : 'Internal error',
        },
      };
    }
  }

  /**
   * Start the stdio event loop
   */
  run(): void {
    if (this.running) {
      return;
    }
    this.running = true;

    const rl = createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false,
    });

    rl.on('line', async (line) => {
      if (!line.trim()) return;

      try {
        const request = JSON.parse(line) as JsonRpcRequest;
        const response = await this.handleRequest(request);
        console.log(JSON.stringify(response));
      } catch (error) {
        const errorResponse: JsonRpcResponse = {
          jsonrpc: '2.0',
          id: 0,
          error: {
            code: -32700,
            message: 'Parse error',
          },
        };
        console.log(JSON.stringify(errorResponse));
      }
    });

    rl.on('close', () => {
      this.running = false;
      process.exit(0);
    });
  }

  /**
   * Stop the worker
   */
  stop(): void {
    this.running = false;
  }

  /**
   * Check if worker is running
   */
  isRunning(): boolean {
    return this.running;
  }
}
