from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Path, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ..models.orders import OrderResponse

router = APIRouter()
security = HTTPBearer()


@router.get("/", response_model=OrderResponse)
async def get_order(
    order_id: UUID = Path(..., description="Order ID"),
    include_customer_details: bool = Query(True, description="Include full customer details"),
    include_payment_details: bool = Query(False, description="Include payment details"),
    token: str = Depends(security)
) -> OrderResponse:
    """Get order by ID with optional detail levels"""
    # Mock implementation
    raise HTTPException(status_code=404, detail="Order not found")
