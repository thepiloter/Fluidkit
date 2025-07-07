/**
 * FluidKit Runtime Utilities
 * Auto-generated TypeScript utilities for FluidKit fetch wrappers
 */

export interface ApiResult<T = any> {
  data?: T;
  error?: string;
  status: number;
  success: boolean;
}

export function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return '/api';
  }
  return process.env.FASTAPI_URL || 'http://localhost:8000';
}

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
    return { data: responseData, status, success: true };
  } catch (e) {
    return { 
      error: 'Failed to parse response JSON', 
      status, 
      success: false 
    };
  }
}
