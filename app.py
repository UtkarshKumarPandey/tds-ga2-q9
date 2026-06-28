from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import time
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 51
RATE_LIMIT = 15
WINDOW = 10

idempotency = {}
buckets = {}


class Order(BaseModel):
    item: Optional[str] = "demo"


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/orders", status_code=201)
def create_order(
    order: Order,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    if idempotency_key in idempotency:
        return idempotency[idempotency_key]

    obj = {
        "id": str(uuid.uuid4()),
        "item": order.item,
    }

    idempotency[idempotency_key] = obj
    return obj


@app.get("/orders")
def list_orders(
    limit: int = 10,
    cursor: str = "0",
    x_client_id: str = Header(..., alias="X-Client-Id"),
):
    now = time.time()

    hits = buckets.get(x_client_id, [])
    hits = [t for t in hits if now - t < WINDOW]

    if len(hits) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "10"},
        )

    hits.append(now)
    buckets[x_client_id] = hits

    start = int(cursor)

    items = [
        {"id": i}
        for i in range(start + 1, min(start + limit + 1, TOTAL_ORDERS + 1))
    ]

    next_cursor = None
    if items and items[-1]["id"] < TOTAL_ORDERS:
        next_cursor = str(items[-1]["id"])

    return {
        "items": items,
        "next_cursor": next_cursor,
    }
