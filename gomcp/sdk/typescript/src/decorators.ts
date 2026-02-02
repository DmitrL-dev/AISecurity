/**
 * Tool decorator system for GoMCP TypeScript SDK
 */

import { z, ZodType } from 'zod';
import type { ToolDefinition, ToolHandler, ToolMetadata, ToolResult } from './types.js';
import { ok, err, ErrorCode } from './types.js';

// Symbol for storing tool metadata
const TOOL_METADATA = Symbol('tool_metadata');

// Registry of all decorated tools
const toolRegistry = new Map<string, ToolMetadata>();

/**
 * Options for the @tool decorator
 */
export interface ToolOptions<TSchema extends ZodType = ZodType> {
  /** Human-readable description of the tool */
  description: string;
  /** Zod schema for input validation */
  schema?: TSchema;
  /** Default timeout in milliseconds */
  timeoutMs?: number;
}

/**
 * Convert Zod schema to JSON Schema
 */
function zodToJsonSchema(schema: ZodType): Record<string, unknown> {
  // Simplified conversion - in production use zod-to-json-schema
  const def = schema._def;
  
  if ('typeName' in def) {
    switch (def.typeName) {
      case 'ZodString':
        return { type: 'string' };
      case 'ZodNumber':
        return { type: 'number' };
      case 'ZodBoolean':
        return { type: 'boolean' };
      case 'ZodObject':
        const shape = (def as { shape: () => Record<string, ZodType> }).shape();
        const properties: Record<string, unknown> = {};
        const required: string[] = [];
        
        for (const [key, value] of Object.entries(shape)) {
          properties[key] = zodToJsonSchema(value as ZodType);
          // Check if not optional
          if (!('_def' in value && (value as ZodType)._def.typeName === 'ZodOptional')) {
            required.push(key);
          }
        }
        
        return {
          type: 'object',
          properties,
          required: required.length > 0 ? required : undefined,
        };
      case 'ZodArray':
        return {
          type: 'array',
          items: zodToJsonSchema((def as { type: ZodType }).type),
        };
      default:
        return { type: 'any' };
    }
  }
  
  return { type: 'any' };
}

/**
 * Decorator to mark a function as an MCP tool
 * 
 * @example
 * ```typescript
 * const addSchema = z.object({
 *   a: z.number(),
 *   b: z.number(),
 * });
 * 
 * @tool({ description: 'Add two numbers', schema: addSchema })
 * function add(input: z.infer<typeof addSchema>): ToolResult<number> {
 *   return ok(input.a + input.b);
 * }
 * ```
 */
export function tool<TSchema extends ZodType>(options: ToolOptions<TSchema>) {
  return function<T extends ToolHandler>(
    target: T,
    context: ClassMethodDecoratorContext | undefined
  ): T {
    const name = context?.name?.toString() ?? target.name;
    
    const definition: ToolDefinition = {
      name,
      description: options.description,
      inputSchema: options.schema ? zodToJsonSchema(options.schema) : {},
      defaultTimeoutMs: options.timeoutMs ?? 30000,
    };

    // Create wrapped handler with validation
    const wrappedHandler: ToolHandler = async (input: unknown) => {
      // Validate input if schema provided
      if (options.schema) {
        const result = options.schema.safeParse(input);
        if (!result.success) {
          return err(
            ErrorCode.InvalidArguments,
            'Invalid input',
            result.error.format()._errors.join(', ')
          );
        }
        input = result.data;
      }
      
      try {
        return await target(input);
      } catch (error) {
        return err(
          ErrorCode.Unknown,
          error instanceof Error ? error.message : 'Unknown error'
        );
      }
    };

    const metadata: ToolMetadata = {
      definition,
      handler: wrappedHandler,
    };

    // Store in registry
    toolRegistry.set(name, metadata);
    
    // Also attach to function for direct access
    (target as unknown as { [TOOL_METADATA]: ToolMetadata })[TOOL_METADATA] = metadata;

    return target;
  };
}

/**
 * Create a tool from a function (alternative to decorator)
 */
export function createTool<TInput, TOutput>(
  name: string,
  options: ToolOptions,
  handler: (input: TInput) => Promise<ToolResult<TOutput>> | ToolResult<TOutput>
): ToolMetadata {
  const definition: ToolDefinition = {
    name,
    description: options.description,
    inputSchema: options.schema ? zodToJsonSchema(options.schema) : {},
    defaultTimeoutMs: options.timeoutMs ?? 30000,
  };

  const wrappedHandler: ToolHandler = async (input: unknown) => {
    if (options.schema) {
      const result = options.schema.safeParse(input);
      if (!result.success) {
        return err(
          ErrorCode.InvalidArguments,
          'Invalid input',
          result.error.format()._errors.join(', ')
        );
      }
      input = result.data;
    }
    
    try {
      return await handler(input as TInput);
    } catch (error) {
      return err(
        ErrorCode.Unknown,
        error instanceof Error ? error.message : 'Unknown error'
      );
    }
  };

  const metadata: ToolMetadata = {
    definition,
    handler: wrappedHandler,
  };

  toolRegistry.set(name, metadata);
  return metadata;
}

/**
 * Get all registered tools
 */
export function getRegisteredTools(): Map<string, ToolMetadata> {
  return new Map(toolRegistry);
}

/**
 * Get a specific tool by name
 */
export function getTool(name: string): ToolMetadata | undefined {
  return toolRegistry.get(name);
}

/**
 * Clear all registered tools (for testing)
 */
export function clearTools(): void {
  toolRegistry.clear();
}

/**
 * Get tool metadata from a decorated function
 */
export function getToolMetadata(fn: unknown): ToolMetadata | undefined {
  return (fn as { [TOOL_METADATA]?: ToolMetadata })[TOOL_METADATA];
}

// Re-export useful items
export { ok, err, ErrorCode };
export type { ToolResult, ToolDefinition, ToolMetadata };
