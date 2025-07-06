import { ApiResult, getBaseUrl, handleResponse } from './.fluidkit/fluidkit';

/**
 * @property ACTIVE
 * @property INACTIVE
 * @property BANNED
 */
export enum UserStatus {
  ACTIVE = "active",
  INACTIVE = "inactive",
  BANNED = "banned",
}

/**
 * @property LOW
 * @property HIGH
 */
export enum Priority {
  LOW = 1,
  HIGH = 2,
}

/**
 * @property priority
 * @property field2
 */
export interface User {
  /** @default Priority.LOW */
  priority?: Priority;
  /** @default UserStatus.ACTIVE */
  field2?: UserStatus;
}

/**
 * Complete test interface
 *
 * @property name - The user's name
 * @property data
 * @property result
 */
export interface CompleteTest {
  /**
   * The user's name
   * @default "aswanth"
   */
  name?: string;
  data: Record<string, (string | number | null)[]>;
  result?: string | number | null;
}

/**
 * @property name
 */
export interface Manager {
  /** @default "aswanth" */
  name?: string;
}

/**
 * @param user_data
 * @param status
 * @param priority
 * @param options - Additional fetch options
 */
export async function create_user(user_data: CompleteTest, status?: UserStatus, priority?: Priority, options?: RequestInit): Promise<ApiResult<any>> {
  let url = `${getBaseUrl()}/users`;

  const searchParams = new URLSearchParams();
  if (status !== undefined) {
    searchParams.set('status', String(status));
  }
  if (priority !== undefined) {
    searchParams.set('priority', String(priority));
  }
  if (searchParams.toString()) {
    url += `?${searchParams.toString()}`;
  }

  const requestOptions: RequestInit = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    },
    body: JSON.stringify(user_data),
    ...options
  };

  const response = await fetch(url, requestOptions);
  return handleResponse(response);
}