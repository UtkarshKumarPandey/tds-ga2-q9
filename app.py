from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import time

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

idempotency_store = {}
rate_store = {}


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
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    obj = {
        "id": str(uuid.uuid4()),
        "item": order.item,
    }

    idempotency_store[idempotency_key] = obj
    return obj


@app.get("/orders")
def get_orders(
    limit: int = 10,
    cursor: str = "0",
    x_client_id: str = Header(..., alias="X-Client-Id"),
):
    now = time.time()

    timestamps = rate_store.get(x_client_id, [])
    timestamps = [t for t in timestamps if now - t < WINDOW]

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "Retry-After": "10"
            },
        )

    timestamps.append(now)
    rate_store[x_client_id] = timestamps

    start = int(cursor)

    items = []

    end = min(start + limit, TOTAL_ORDERS)

    for i in range(start + 1, end + 1):
        items.append({
            "id": i
        })

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = str(end)

    return {
        "items": items,
        "next_cursor": next_cursor,
    }
