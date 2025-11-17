import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Collection as CollectionSchema, Inventory as InventorySchema, Review as ReviewSchema, Order as OrderSchema, Config as ConfigSchema

app = FastAPI(title="The Gilded Gaze API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class ObjectIdStr(str):
    pass


def to_oid(oid: str):
    try:
        return ObjectId(oid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


# Health
@app.get("/")
def read_root():
    return {"message": "The Gilded Gaze API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Schemas exposed for admin/viewer
@app.get("/schema")
def get_schema():
    return {
        "collections": [
            "config", "collection", "product", "inventory", "review", "order"
        ]
    }


# Seed minimal data if empty
@app.post("/seed")
def seed():
    # Config
    if db["config"].count_documents({}) == 0:
        create_document("config", ConfigSchema(limited_edition_active=False, limited_edition_name="Celestial Gaze"))
    # Collections
    if db["collection"].count_documents({}) == 0:
        create_document("collection", CollectionSchema(handle="core", title="The Gilded Gaze", description="Quiet luxury for timeless radiance", is_limited=False))
        create_document("collection", CollectionSchema(handle="celestial-gaze", title="Celestial Gaze", description="Limited edition celestial hues", is_limited=True))
    # Products example
    if db["product"].count_documents({}) == 0:
        # Core product
        core_id = create_document("product", ProductSchema(
            title="The Classic Heirloom",
            subtitle="Effortless elegance",
            description="A refined cluster that enhances with subtle grace.",
            price=24.0,
            collection_handle="core",
            image=None,
            limited_badge=None,
            is_bundle=False
        ))
        create_document("inventory", InventorySchema(product_id=core_id, quantity=50))
        # Celestial products
        pids = []
        for title, subtitle in [
            ("The Sapphire Serenity", "composure & poise"),
            ("The Amethyst Aura", "intuition & depth"),
            ("The Rose Gold Reverie", "warmth & allure")
        ]:
            pid = create_document("product", ProductSchema(
                title=title,
                subtitle=subtitle,
                description="Limited edition celestial-inspired clusters.",
                price=28.0,
                compare_at_price=32.0,
                collection_handle="celestial-gaze",
                image=None,
                limited_badge="Limited Edition",
                is_bundle=False
            ))
            create_document("inventory", InventorySchema(product_id=pid, quantity=20))
            pids.append(pid)
        # Bundle
        bundle_id = create_document("product", ProductSchema(
            title="The Celestial Kit",
            subtitle="Complete limited edition set",
            description="All three celestial styles in one heirloom-worthy ensemble.",
            price=72.0,
            compare_at_price=84.0,
            collection_handle="celestial-gaze",
            image=None,
            limited_badge="Limited Edition",
            is_bundle=True
        ))
        create_document("inventory", InventorySchema(product_id=bundle_id, quantity=10))
    return {"status": "seeded"}


# Config endpoints
@app.get("/config")
def get_config():
    doc = db["config"].find_one({})
    if not doc:
        return {"limited_edition_active": False, "limited_edition_name": "Celestial Gaze"}
    doc["_id"] = str(doc["_id"]) if "_id" in doc else None
    return doc


class ConfigToggle(BaseModel):
    limited_edition_active: bool


@app.post("/config/toggle")
def toggle_config(payload: ConfigToggle):
    existing = db["config"].find_one({})
    if existing:
        db["config"].update_one({"_id": existing["_id"]}, {"$set": {"limited_edition_active": payload.limited_edition_active}})
    else:
        create_document("config", ConfigSchema(limited_edition_active=payload.limited_edition_active))
    return {"ok": True, "limited_edition_active": payload.limited_edition_active}


# Products
@app.get("/collections/{handle}/products")
def list_products(handle: str):
    products = get_documents("product", {"collection_handle": handle})
    for p in products:
        p["_id"] = str(p["_id"]) if "_id" in p else None
        inv = db["inventory"].find_one({"product_id": str(p["_id"])})
        p["inventory"] = inv["quantity"] if inv else 0
    return products


@app.get("/products/{product_id}")
def get_product(product_id: str):
    prod = db["product"].find_one({"_id": to_oid(product_id)})
    if not prod:
        raise HTTPException(404, "Product not found")
    prod["_id"] = str(prod["_id"]) if "_id" in prod else None
    inv = db["inventory"].find_one({"product_id": product_id})
    prod["inventory"] = inv["quantity"] if inv else 0
    return prod


# Cart/Checkout (mock, no payment gateway for demo)
class AddToCart(BaseModel):
    product_id: str
    quantity: int = 1


@app.post("/checkout")
def checkout(order: OrderSchema):
    # Reduce inventory and create order record
    for item in order.items:
        inv = db["inventory"].find_one({"product_id": item.product_id})
        if not inv or inv.get("quantity", 0) < item.quantity:
            raise HTTPException(400, f"Insufficient stock for {item.title}")
    # Deduct
    for item in order.items:
        db["inventory"].update_one({"product_id": item.product_id}, {"$inc": {"quantity": -item.quantity}})
    oid = create_document("order", order)
    return {"ok": True, "order_id": oid}


# Reviews
@app.get("/products/{product_id}/reviews")
def get_reviews(product_id: str):
    reviews = get_documents("review", {"product_id": product_id})
    for r in reviews:
        r["_id"] = str(r["_id"]) if "_id" in r else None
    return reviews


class NewReview(BaseModel):
    author: str
    rating: int
    content: str


@app.post("/products/{product_id}/reviews")
def add_review(product_id: str, payload: NewReview):
    rid = create_document("review", ReviewSchema(product_id=product_id, author=payload.author, rating=payload.rating, content=payload.content))
    return {"ok": True, "review_id": rid}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
