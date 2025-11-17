"""
Database Schemas for The Gilded Gaze

Each Pydantic model represents a collection in MongoDB. The collection name is the lowercase of the class name.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class Config(BaseModel):
    """
    Global site configuration
    Collection: "config"
    """
    limited_edition_active: bool = Field(False, description="Whether Celestial Gaze launch is active")
    limited_edition_name: str = Field("Celestial Gaze", description="Limited edition display name")


class Collection(BaseModel):
    """
    Product collections (e.g., Core, Celestial Gaze)
    Collection: "collection"
    """
    handle: str = Field(..., description="URL-safe handle, e.g., 'core' or 'celestial-gaze'")
    title: str = Field(..., description="Display title")
    description: Optional[str] = Field(None, description="Marketing description")
    is_limited: bool = Field(False, description="Whether this is a limited edition collection")


class Product(BaseModel):
    """
    Products (individual lash clusters and bundles)
    Collection: "product"
    """
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price for discounts")
    collection_handle: str = Field(..., description="Handle of parent collection")
    image: Optional[str] = Field(None, description="Image URL")
    limited_badge: Optional[str] = Field(None, description="Badge text like 'Limited Edition'")
    is_bundle: bool = Field(False, description="True if this is a bundle product")


class Inventory(BaseModel):
    """
    Inventory tracking per product
    Collection: "inventory"
    """
    product_id: str = Field(..., description="Stringified ObjectId of product")
    quantity: int = Field(..., ge=0)


class Review(BaseModel):
    """
    Customer reviews
    Collection: "review"
    """
    product_id: str
    author: str
    rating: int = Field(..., ge=1, le=5)
    content: str


class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(..., ge=1)


class Order(BaseModel):
    """
    Orders (simple mock checkout)
    Collection: "order"
    """
    items: List[OrderItem]
    subtotal: float
    email: str
    name: Optional[str] = None
    address: Optional[str] = None
