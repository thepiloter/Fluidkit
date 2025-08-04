import json
import asyncio
from typing import List, Optional, AsyncGenerator
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sse_starlette import EventSourceResponse
from starlette.responses import StreamingResponse

from ..models.orders import (
    Order, OrderResponse, OrderListResponse, CreateOrderRequest,
    OrderStatus, ShippingMethod
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    page: int = 1,
    per_page: int = 10,
    status: Optional[OrderStatus] = None,
    customer_id: Optional[UUID] = None
) -> OrderListResponse:
    """List orders with filtering"""
    return OrderListResponse(
        orders=[],
        total=0,
        page=page,
        has_next=False
    )


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: CreateOrderRequest,
    auto_confirm: bool = False,
    send_confirmation_email: bool = True
) -> OrderResponse:
    """Create a new order"""
    raise HTTPException(status_code=400, detail="Order creation failed")


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    status: Optional[OrderStatus] = None,
    shipping_method: Optional[ShippingMethod] = None,
    notify_customer: bool = True
) -> OrderResponse:
    """Update order"""
    raise HTTPException(status_code=404, detail="Order not found")


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    reason: str,
    refund_amount: Optional[float] = None,
    notify_customer: bool = True
) -> OrderResponse:
    """Cancel order with refund"""
    raise HTTPException(status_code=404, detail="Order not found")


# === STREAMING ENDPOINTS === #

async def generate_order_updates(order_id: UUID) -> AsyncGenerator[str, None]:
    """Generate real-time order status updates"""
    statuses = ["confirmed", "processing", "shipped", "delivered"]
    
    for status in statuses:
        event = {
            "order_id": str(order_id),
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "message": f"Order {status}"
        }
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(2)


@router.get("/{order_id}/updates")
async def stream_order_updates(order_id: UUID) -> EventSourceResponse:
    """Stream real-time order status updates"""
    return EventSourceResponse(generate_order_updates(order_id))


async def generate_order_reports() -> AsyncGenerator[bytes, None]:
    """Generate streaming order reports"""
    for hour in range(24):
        data = {
            "hour": hour,
            "orders_count": 10 + hour,
            "revenue": 1000.0 + (hour * 50),
            "avg_order_value": 75.50 + hour
        }
        yield f"{json.dumps(data)}\n".encode()
        await asyncio.sleep(0.3)


@router.get("/reports/stream")
async def stream_order_reports() -> StreamingResponse:
    """Stream order analytics reports"""
    return StreamingResponse(
        generate_order_reports(),
        media_type="application/x-ndjson"
    )
