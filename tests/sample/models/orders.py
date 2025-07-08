from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Union, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl
from pydantic_extra_types.payment import PaymentCardNumber

from .users import User, Address, PaymentMethod


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class ShippingMethod(str, Enum):
    """Shipping method options"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    PICKUP = "pickup"


class ProductCategory(BaseModel):
    """Product category information"""
    id: UUID
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[UUID] = None


class Product(BaseModel):
    """Product information"""
    id: UUID = Field(..., description="Product ID")
    sku: str = Field(..., max_length=50, description="Stock keeping unit")
    name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: ProductCategory
    
    # Pricing with Decimal for precision
    price: Decimal = Field(..., max_digits=10, decimal_places=2, gt=0)
    compare_at_price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    cost: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    
    # Inventory
    stock_quantity: int = Field(..., ge=0)
    track_inventory: bool = Field(default=True)
    
    # Metadata
    weight: Optional[Decimal] = Field(None, max_digits=8, decimal_places=3)
    dimensions: Optional[Dict[str, float]] = None  # {"length": 10.5, "width": 5.0, "height": 2.0}
    images: List[HttpUrl] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class OrderItem(BaseModel):
    """Individual item in an order"""
    id: UUID = Field(default_factory=UUID)
    product: Product
    quantity: int = Field(..., gt=0, le=1000)
    unit_price: Decimal = Field(..., max_digits=10, decimal_places=2)
    total_price: Decimal = Field(..., max_digits=10, decimal_places=2)
    
    # Optional customization
    customization: Optional[Dict[str, Any]] = None
    gift_message: Optional[str] = Field(None, max_length=500)


class ShippingInfo(BaseModel):
    """Shipping information"""
    method: ShippingMethod = Field(default=ShippingMethod.STANDARD)
    carrier: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=100)
    tracking_url: Optional[HttpUrl] = None
    
    # Shipping address
    address: Address
    
    # Timing
    estimated_delivery: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Costs
    shipping_cost: Decimal = Field(default=Decimal("0.00"), max_digits=8, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), max_digits=8, decimal_places=2)


class PaymentInfo(BaseModel):
    """Payment information"""
    method: PaymentMethod
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    
    # Transaction details
    transaction_id: Optional[str] = Field(None, max_length=100)
    authorization_code: Optional[str] = Field(None, max_length=100)
    
    # Amounts
    subtotal: Decimal = Field(..., max_digits=10, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    shipping_amount: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    total_amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    
    # Timestamps
    authorized_at: Optional[datetime] = None
    captured_at: Optional[datetime] = None


class Order(BaseModel):
    """Main order model with complex relationships"""
    id: UUID = Field(..., description="Order ID")
    order_number: str = Field(..., max_length=50, description="Human-readable order number")
    
    # Customer and status
    customer: User  # Reference to User model from users.py
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    
    # Order contents
    items: List[OrderItem] = Field(..., min_items=1)
    
    # Shipping and payment
    shipping_info: ShippingInfo
    payment_info: PaymentInfo
    
    # Timestamps with complex datetime usage
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now() + timedelta(hours=24)
    )
    
    # Notes and metadata
    customer_notes: Optional[str] = Field(None, max_length=1000)
    internal_notes: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateOrderRequest(BaseModel):
    """Request model for creating orders"""
    customer_id: UUID
    items: List[Dict[str, Union[UUID, int]]]  # [{"product_id": UUID, "quantity": int}]
    shipping_address: Address
    payment_method_id: UUID
    shipping_method: ShippingMethod = Field(default=ShippingMethod.STANDARD)
    customer_notes: Optional[str] = Field(None, max_length=1000)


class UpdateOrderRequest(BaseModel):
    """Request model for updating orders"""
    status: Optional[OrderStatus] = None
    shipping_method: Optional[ShippingMethod] = None
    tracking_number: Optional[str] = Field(None, max_length=100)
    internal_notes: Optional[str] = Field(None, max_length=2000)


class OrderResponse(BaseModel):
    """Response model for order data"""
    id: UUID
    order_number: str
    customer: User  # Full customer data
    status: OrderStatus
    items: List[OrderItem]
    shipping_info: ShippingInfo
    payment_info: PaymentInfo
    created_at: datetime
    updated_at: Optional[datetime]
    expires_at: Optional[datetime]


class OrderSummary(BaseModel):
    """Lightweight order summary for lists"""
    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    status: OrderStatus
    total_amount: Decimal
    item_count: int
    created_at: datetime


class OrderListResponse(BaseModel):
    """Paginated order list response"""
    orders: List[OrderSummary]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    has_next: bool
    has_prev: bool
