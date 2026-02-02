import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GoMCPClient, GoMCPError, createClient } from '../src/client';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('GoMCPClient', () => {
  let client: GoMCPClient;

  beforeEach(() => {
    vi.resetAllMocks();
    client = new GoMCPClient({ baseUrl: 'http://localhost:8080' });
  });

  describe('constructor', () => {
    it('should remove trailing slash from baseUrl', () => {
      const c = new GoMCPClient({ baseUrl: 'http://example.com/' });
      expect(c['baseUrl']).toBe('http://example.com');
    });

    it('should use default timeout', () => {
      expect(client['timeout']).toBe(30000);
    });

    it('should use custom timeout', () => {
      const c = new GoMCPClient({ baseUrl: 'http://localhost', timeout: 5000 });
      expect(c['timeout']).toBe(5000);
    });
  });

  describe('listTools', () => {
    it('should return list of tools', async () => {
      const tools = [{ name: 'tool1', description: 'desc' }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(tools)
      });

      const result = await client.listTools();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/v1/tools',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toEqual(tools);
    });
  });

  describe('callTool', () => {
    it('should call tool with arguments', async () => {
      const response = { success: true, output: { data: 'test' }, latency: '10ms' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(response)
      });

      const result = await client.callTool('echo', { msg: 'hello' });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/v1/tools/call',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ tool: 'echo', arguments: { msg: 'hello' } })
        })
      );
      expect(result.success).toBe(true);
    });

    it('should include tenant_id when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, latency: '5ms' })
      });

      await client.callTool('tool', {}, 'tenant1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"tenant_id":"tenant1"')
        })
      );
    });
  });

  describe('batchCall', () => {
    it('should batch call tools', async () => {
      const response = {
        responses: [{ success: true, latency: '5ms' }],
        total_latency: '10ms',
        success_count: 1,
        error_count: 0
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(response)
      });

      const result = await client.batchCall([
        { tool: 't1', arguments: {} }
      ]);

      expect(result.success_count).toBe(1);
    });

    it('should support parallel execution', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          responses: [],
          total_latency: '5ms',
          success_count: 0,
          error_count: 0
        })
      });

      await client.batchCall([], { parallel: true, maxParallel: 5 });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"parallel":true')
        })
      );
    });
  });

  describe('health', () => {
    it('should get health status', async () => {
      const health = { status: 'healthy', version: '1.0.0', uptime: '1h' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(health)
      });

      const result = await client.health();

      expect(result.status).toBe('healthy');
    });
  });

  describe('liveness', () => {
    it('should return true when healthy', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      });

      const result = await client.liveness();
      expect(result).toBe(true);
    });

    it('should return false on error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await client.liveness();
      expect(result).toBe(false);
    });
  });

  describe('readiness', () => {
    it('should return true when ready', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ ready: true })
      });

      const result = await client.readiness();
      expect(result).toBe(true);
    });

    it('should return false when not ready', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ ready: false })
      });

      const result = await client.readiness();
      expect(result).toBe(false);
    });
  });

  describe('error handling', () => {
    it('should throw GoMCPError on HTTP error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      });

      await expect(client.listTools()).rejects.toThrow(GoMCPError);
    });

    it('should include status code in error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Not Found')
      });

      try {
        await client.listTools();
      } catch (error) {
        expect(error).toBeInstanceOf(GoMCPError);
        expect((error as GoMCPError).statusCode).toBe(404);
      }
    });
  });
});

describe('createClient', () => {
  it('should create client with base URL', () => {
    const client = createClient('http://localhost:8080');
    expect(client).toBeInstanceOf(GoMCPClient);
  });

  it('should accept options', () => {
    const client = createClient('http://localhost:8080', { timeout: 10000 });
    expect(client['timeout']).toBe(10000);
  });
});

describe('GoMCPError', () => {
  it('should create error with message', () => {
    const error = new GoMCPError('Test error');
    expect(error.message).toBe('Test error');
    expect(error.name).toBe('GoMCPError');
  });

  it('should include status code', () => {
    const error = new GoMCPError('Error', 500);
    expect(error.statusCode).toBe(500);
  });

  it('should include response', () => {
    const error = new GoMCPError('Error', 400, { detail: 'Invalid' });
    expect(error.response).toEqual({ detail: 'Invalid' });
  });
});
