/**
 * Tests for GoMCP TypeScript SDK
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { z } from 'zod';
import {
  ErrorCode,
  ok,
  err,
  createTool,
  getRegisteredTools,
  getTool,
  clearTools,
  type ToolResult,
} from '../src/index.js';
import { Worker } from '../src/worker.js';

describe('Types', () => {
  describe('ok()', () => {
    it('creates a successful result', () => {
      const result = ok({ data: 'test' });
      expect(result.output).toEqual({ data: 'test' });
      expect(result.error).toBeUndefined();
    });

    it('includes duration when provided', () => {
      const result = ok('hello', 100);
      expect(result.output).toBe('hello');
      expect(result.durationMs).toBe(100);
    });
  });

  describe('err()', () => {
    it('creates a failed result', () => {
      const result = err(ErrorCode.Timeout, 'Operation timed out');
      expect(result.error?.code).toBe(ErrorCode.Timeout);
      expect(result.error?.message).toBe('Operation timed out');
    });

    it('includes details when provided', () => {
      const result = err(ErrorCode.InvalidArguments, 'Bad input', 'field "name" required');
      expect(result.error?.details).toBe('field "name" required');
    });
  });
});

describe('createTool', () => {
  beforeEach(() => {
    clearTools();
  });

  it('registers a tool with basic options', () => {
    createTool<{ name: string }, string>(
      'greet',
      { description: 'Greets a person' },
      (input) => ok(`Hello, ${input.name}!`)
    );

    const tool = getTool('greet');
    expect(tool).toBeDefined();
    expect(tool?.definition.name).toBe('greet');
    expect(tool?.definition.description).toBe('Greets a person');
  });

  it('validates input with Zod schema', async () => {
    const schema = z.object({
      a: z.number(),
      b: z.number(),
    });

    createTool<z.infer<typeof schema>, number>(
      'add',
      { description: 'Adds numbers', schema },
      (input) => ok(input.a + input.b)
    );

    const tool = getTool('add');
    expect(tool).toBeDefined();

    // Valid input
    const result1 = await tool!.handler({ a: 5, b: 3 });
    expect(result1.output).toBe(8);

    // Invalid input
    const result2 = await tool!.handler({ a: 'not a number', b: 3 });
    expect(result2.error?.code).toBe(ErrorCode.InvalidArguments);
  });

  it('generates JSON schema from Zod', () => {
    const schema = z.object({
      name: z.string(),
      age: z.number(),
    });

    createTool(
      'test',
      { description: 'Test tool', schema },
      () => ok('ok')
    );

    const tool = getTool('test');
    expect(tool?.definition.inputSchema).toEqual({
      type: 'object',
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
      required: ['name', 'age'],
    });
  });

  it('handles async handlers', async () => {
    createTool<void, string>(
      'async_tool',
      { description: 'Async tool' },
      async () => {
        await new Promise((r) => setTimeout(r, 10));
        return ok('async result');
      }
    );

    const tool = getTool('async_tool');
    const result = await tool!.handler({});
    expect(result.output).toBe('async result');
  });

  it('catches handler errors', async () => {
    createTool<void, never>(
      'broken_tool',
      { description: 'Throws an error' },
      () => {
        throw new Error('Something went wrong');
      }
    );

    const tool = getTool('broken_tool');
    const result = await tool!.handler({});
    expect(result.error?.code).toBe(ErrorCode.Unknown);
    expect(result.error?.message).toBe('Something went wrong');
  });
});

describe('getRegisteredTools', () => {
  beforeEach(() => {
    clearTools();
  });

  it('returns all registered tools', () => {
    createTool('tool1', { description: 'Tool 1' }, () => ok('1'));
    createTool('tool2', { description: 'Tool 2' }, () => ok('2'));
    createTool('tool3', { description: 'Tool 3' }, () => ok('3'));

    const tools = getRegisteredTools();
    expect(tools.size).toBe(3);
    expect(tools.has('tool1')).toBe(true);
    expect(tools.has('tool2')).toBe(true);
    expect(tools.has('tool3')).toBe(true);
  });
});

describe('Worker', () => {
  beforeEach(() => {
    clearTools();
  });

  it('creates with default config', () => {
    const worker = new Worker();
    expect(worker.isRunning()).toBe(false);
  });

  it('returns tool definitions', () => {
    createTool('test', { description: 'Test tool' }, () => ok('ok'));
    
    const worker = new Worker();
    const defs = worker.getToolDefinitions();
    
    expect(defs.length).toBe(1);
    expect(defs[0].name).toBe('test');
  });

  it('calls tools by name', async () => {
    createTool<{ x: number }, number>(
      'double',
      { description: 'Doubles a number' },
      (input) => ok(input.x * 2)
    );

    const worker = new Worker();
    const result = await worker.callTool('double', { x: 21 });
    
    expect(result.output).toBe(42);
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('returns error for unknown tool', async () => {
    const worker = new Worker();
    const result = await worker.callTool('nonexistent', {});
    
    expect(result.error?.code).toBe(ErrorCode.ToolNotFound);
  });

  it('handles initialize request', async () => {
    const worker = new Worker({ name: 'test-worker' });
    const response = await worker.handleRequest({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
    });

    expect(response.result).toEqual({
      protocolVersion: '1.0',
      capabilities: { tools: {} },
      serverInfo: { name: 'test-worker', version: '1.0.0' },
    });
  });

  it('handles tools/list request', async () => {
    createTool('test', { description: 'Test' }, () => ok(''));
    
    const worker = new Worker();
    const response = await worker.handleRequest({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
    });

    expect(response.result).toEqual({
      tools: [{ name: 'test', description: 'Test', inputSchema: {} }],
    });
  });

  it('handles tools/call request', async () => {
    createTool<{ msg: string }, string>(
      'echo',
      { description: 'Echoes message' },
      (input) => ok(input.msg)
    );

    const worker = new Worker();
    const response = await worker.handleRequest({
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: { name: 'echo', arguments: { msg: 'hello' } },
    });

    expect(response.result).toEqual({
      content: [{ type: 'text', text: 'hello' }],
    });
  });

  it('handles ping request', async () => {
    const worker = new Worker();
    const response = await worker.handleRequest({
      jsonrpc: '2.0',
      id: 4,
      method: 'ping',
    });

    expect(response.result).toEqual({ pong: true });
  });

  it('returns error for unknown method', async () => {
    const worker = new Worker();
    const response = await worker.handleRequest({
      jsonrpc: '2.0',
      id: 5,
      method: 'unknown/method',
    });

    expect(response.error?.code).toBe(-32601);
    expect(response.error?.message).toContain('Method not found');
  });
});
