from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from .users import User, Address


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ShippingMethod(str, Enum):
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"


class OrderItem(BaseModel):
    id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class Order(BaseModel):
    id: UUID
    order_number: str
    customer: User
    status: OrderStatus
    items: List[OrderItem]
    shipping_address: Address
    shipping_method: ShippingMethod
    total_amount: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreateOrderRequest(BaseModel):
    customer_id: UUID
    items: List[dict]
    shipping_address: Address
    shipping_method: ShippingMethod = ShippingMethod.STANDARD


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    customer: User
    status: OrderStatus
    items: List[OrderItem]
    total_amount: Decimal
    created_at: datetime


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    has_next: bool
