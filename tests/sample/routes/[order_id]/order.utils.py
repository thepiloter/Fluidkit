from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from ...models.orders import OrderResponse as OrderResp


router = APIRouter()


@router.get("/", response_model=OrderResp)
async def get_order(
    order_id: UUID,
    include_customer_details: bool = True,
    include_payment_details: bool = False
) -> OrderResp:
    """Get order by ID with optional details"""
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/tracking")
async def get_order_tracking(
    order_id: UUID,
    detailed: bool = False
) -> dict:
    """Get order tracking information"""
    return {
        "order_id": str(order_id),
        "tracking_number": "1Z999AA1234567890",
        "status": "in_transit",
        "estimated_delivery": "2024-01-15"
    }
