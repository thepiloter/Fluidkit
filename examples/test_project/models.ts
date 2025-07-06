import { BaseModel } from './pydantic';

/**
 * @property id
 * @property name - User name
 * @property email
 */
export interface User {
  id: number;
  /** User name */
  name: string;
  email?: string;
}

/**
 * @property name
 * @property price
 */
export interface Product {
  name: string;
  price: number;
}