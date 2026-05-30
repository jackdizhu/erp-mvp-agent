from pydantic import BaseModel
from typing import Optional


class OrderItem(BaseModel):
    sku: str
    name: str
    qty: int
    price: float = 0


class Order(BaseModel):
    order_id: str
    type: str
    status: str = "pending"
    customer: Optional[str] = None
    items: list[OrderItem] = []
    total: float = 0
    address: Optional[str] = None
    supplier: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    estimated_delivery: Optional[str] = None
    cancel_reason: Optional[str] = None
    notes: str = ""


class InventoryItem(BaseModel):
    sku: str
    name: str
    qty: int
    reserved: int = 0
    available: int = 0
    unit: str = "台"
    unit_price: float = 0
    location: Optional[str] = None
    reorder_point: int = 0
    updated_at: Optional[str] = None


class SupplierItem(BaseModel):
    sku: str


class Supplier(BaseModel):
    supplier_id: str
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    items: list[str] = []
    lead_time_days: int = 0
    status: str = "active"
