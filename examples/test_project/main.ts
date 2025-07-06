import { User } from './models';

import { ApiResult, getBaseUrl, handleResponse } from './.fluidkit/fluidkit';

/**
 * @param user_id
 * @param q
 * @param options - Additional fetch options
 */
export async function get_user(user_id: number, q: string, options?: RequestInit): Promise<ApiResult<any>> {
  let url = `${getBaseUrl()}/users/${user_id}`;

  const searchParams = new URLSearchParams();
  searchParams.set('q', String(q));
  if (searchParams.toString()) {
    url += `?${searchParams.toString()}`;
  }

  const requestOptions: RequestInit = {
    method: 'GET',
    headers: options?.headers,
    ...options
  };

  const response = await fetch(url, requestOptions);
  return handleResponse(response);
}

/**
 * @param user
 * @param options - Additional fetch options
 */
export async function create_user(user: User, options?: RequestInit): Promise<ApiResult<any>> {
  let url = `${getBaseUrl()}/users`;

  const requestOptions: RequestInit = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    },
    body: JSON.stringify(user),
    ...options
  };

  const response = await fetch(url, requestOptions);
  return handleResponse(response);
}