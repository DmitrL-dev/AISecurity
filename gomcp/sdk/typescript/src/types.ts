/**
 * Type definitions for GoMCP TypeScript SDK
 */

/**
 * Error codes matching Go supervisor errors
 */
export enum ErrorCode {
  Unknown = 0,
  Timeout = 1,
  ToolNotFound = 2,
  WorkerCrashed = 3,
  PermissionDenied = 4,
  InvalidArguments = 5,
}

/**
 * Error from tool execution
 */
export interface ToolError {
  code: ErrorCode;
  message: string;
  details?: string;
}

/**
 * Result of tool execution
 */
export interface ToolResult<T = unknown> {
  output?: T;
  error?: ToolError;
  durationMs?: number;
}

/**
 * Create a successful tool result
 */
export function ok<T>(output: T, durationMs?: number): ToolResult<T> {
  return { output, durationMs };
}

/**
 * Create a failed tool result
 */
export function err(code: ErrorCode, message: string, details?: string): ToolResult<never> {
  return { error: { code, message, details } };
}

/**
 * Tool definition for registration
 */
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  defaultTimeoutMs?: number;
}

/**
 * Metadata attached to decorated tool functions
 */
export interface ToolMetadata {
  definition: ToolDefinition;
  handler: ToolHandler;
}

/**
 * Tool handler function type
 */
export type ToolHandler<TInput = unknown, TOutput = unknown> = (
  input: TInput
) => Promise<ToolResult<TOutput>> | ToolResult<TOutput>;

/**
 * JSON-RPC request structure
 */
export interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: unknown;
}

/**
 * JSON-RPC response structure
 */
export interface JsonRpcResponse<T = unknown> {
  jsonrpc: '2.0';
  id: string | number;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/**
 * Worker configuration
 */
export interface WorkerConfig {
  /** Name of the worker for logging */
  name?: string;
  /** Default timeout for tool calls in ms */
  defaultTimeoutMs?: number;
}
