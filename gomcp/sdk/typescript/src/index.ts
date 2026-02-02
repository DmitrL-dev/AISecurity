/**
 * GoMCP TypeScript SDK - Main entry point
 */

// Types
export { 
  ErrorCode,
  ok, 
  err,
  type ToolError,
  type ToolResult,
  type ToolDefinition,
  type ToolMetadata,
  type ToolHandler,
  type JsonRpcRequest,
  type JsonRpcResponse,
  type WorkerConfig,
} from './types.js';

// Decorators
export {
  tool,
  createTool,
  getRegisteredTools,
  getTool,
  clearTools,
  getToolMetadata,
  type ToolOptions,
} from './decorators.js';

// Worker
export { Worker } from './worker.js';

// GoMCP Client (for RLM integration)
export { GoMCPClient, RLMHybridClient } from './goMcpClient.js';

