/**
 * FluidKit Runtime Utilities
 * Auto-generated TypeScript utilities for FluidKit fetch wrappers
 */

export interface ApiResult<T = any> {
  response?: T;           // Successful response data
  error?: string;         // Error message if request failed
  status: number;         // HTTP status code
  success: boolean;       // Convenience property
}

/**
 * Get base URL for API requests
 * Environment-aware: SvelteKit proxy in browser, direct FastAPI on server
 */
export function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Client-side: SvelteKit proxy
    return '/api';
  }
  // Server-side: Direct FastAPI
  return process.env.FASTAPI_URL || 'http://localhost:8000';
}

/**
 * Handle fetch response with typed error handling
 * Non-throwing approach for predictable error handling
 */
export async function handleResponse<T = any>(response: Response): Promise<ApiResult<T>> {
  const status = response.status;
  const success = response.ok;
  
  if (!success) {
    let error: string;
    try {
      const errorBody = await response.json();
      error = errorBody.detail || errorBody.message || response.statusText;
    } catch {
      error = response.statusText || `HTTP ${status}`;
    }
    return { error, status, success: false };
  }
  
  try {
    const responseData = await response.json();
    return { response: responseData, status, success: true };
  } catch (e) {
    return { 
      error: 'Failed to parse response JSON', 
      status, 
      success: false 
    };
  }
}