/**
 * GoMCP TypeScript Client
 * Real HTTP client for communicating with GoMCP HTTP mode server
 */

export interface ToolInfo {
  name: string;
  description: string;
  input_schema?: object;
}

export interface ToolRequest {
  tool: string;
  arguments: object;
  tenant_id?: string;
}

export interface ToolResponse {
  success: boolean;
  output?: unknown;
  error?: string;
  latency: string;
}

export interface BatchRequest {
  requests: ToolRequest[];
  parallel: boolean;
  max_parallel?: number;
}

export interface BatchResponse {
  responses: ToolResponse[];
  total_latency: string;
  success_count: number;
  error_count: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: string;
  components?: Record<string, ComponentHealth>;
}

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message?: string;
}

export interface ClientConfig {
  baseUrl: string;
  timeout?: number;
  tenantId?: string;
  headers?: Record<string, string>;
}

export class GoMCPError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'GoMCPError';
  }
}

/**
 * GoMCP HTTP Client
 * 
 * @example
 * ```typescript
 * const client = new GoMCPClient({ baseUrl: 'http://localhost:8080' });
 * 
 * // List available tools
 * const tools = await client.listTools();
 * 
 * // Call a tool
 * const result = await client.callTool('echo', { message: 'hello' });
 * 
 * // Batch call
 * const batch = await client.batchCall([
 *   { tool: 'tool1', arguments: {} },
 *   { tool: 'tool2', arguments: {} }
 * ], { parallel: true });
 * ```
 */
export class GoMCPClient {
  private baseUrl: string;
  private timeout: number;
  private tenantId?: string;
  private headers: Record<string, string>;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = config.timeout ?? 30000;
    this.tenantId = config.tenantId;
    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers
    };
  }

  /**
   * List available tools
   */
  async listTools(): Promise<ToolInfo[]> {
    const response = await this.fetch('/v1/tools', { method: 'GET' });
    return response as ToolInfo[];
  }

  /**
   * Call a single tool
   */
  async callTool<T = unknown>(
    tool: string,
    args: object = {},
    tenantId?: string
  ): Promise<{ success: boolean; output?: T; error?: string; latency: string }> {
    const request: ToolRequest = {
      tool,
      arguments: args,
      tenant_id: tenantId ?? this.tenantId
    };

    const response = await this.fetch('/v1/tools/call', {
      method: 'POST',
      body: JSON.stringify(request)
    });

    return response as ToolResponse & { output?: T };
  }

  /**
   * Batch call multiple tools
   */
  async batchCall(
    requests: ToolRequest[],
    options: { parallel?: boolean; maxParallel?: number } = {}
  ): Promise<BatchResponse> {
    const batchRequest: BatchRequest = {
      requests,
      parallel: options.parallel ?? false,
      max_parallel: options.maxParallel
    };

    const response = await this.fetch('/v1/tools/batch', {
      method: 'POST',
      body: JSON.stringify(batchRequest)
    });

    return response as BatchResponse;
  }

  /**
   * Get server health status
   */
  async health(): Promise<HealthResponse> {
    const response = await this.fetch('/health', { method: 'GET' });
    return response as HealthResponse;
  }

  /**
   * Liveness check
   */
  async liveness(): Promise<boolean> {
    try {
      await this.fetch('/healthz', { method: 'GET' });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Readiness check
   */
  async readiness(): Promise<boolean> {
    try {
      const response = await this.fetch('/readyz', { method: 'GET' }) as { ready: boolean };
      return response.ready;
    } catch {
      return false;
    }
  }

  private async fetch(path: string, options: RequestInit): Promise<unknown> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        headers: this.headers,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const text = await response.text();
        throw new GoMCPError(
          `HTTP ${response.status}: ${text}`,
          response.status,
          text
        );
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof GoMCPError) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new GoMCPError('Request timeout');
      }

      throw new GoMCPError(`Request failed: ${error}`);
    }
  }
}

/**
 * Create a GoMCP client with default configuration
 */
export function createClient(baseUrl: string, options?: Partial<ClientConfig>): GoMCPClient {
  return new GoMCPClient({
    baseUrl,
    ...options
  });
}

export default GoMCPClient;
