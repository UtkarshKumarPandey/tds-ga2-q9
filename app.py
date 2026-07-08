from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 51
RATE_LIMIT = 15
WINDOW = 10

orders = {}
rate_limit = {}


class Order(BaseModel):
    item: Optional[str] = "demo"


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/orders")
def create_order(
    order: Order,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    if idempotency_key in orders:
        response.status_code = 200
        return orders[idempotency_key]

    obj = {
        "id": str(uuid.uuid4()),
        "item": order.item,
    }

    orders[idempotency_key] = obj
    response.status_code = 201

    return obj


@app.get("/orders")
def list_orders(
    response: Response,
    x_client_id: str = Header(..., alias="X-Client-Id"),
    limit: int = 10,
    cursor: Optional[str] = None,
):
    now = time.time()

    hits = rate_limit.get(x_client_id, [])
    hits = [t for t in hits if now - t < WINDOW]

    if len(hits) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": "10"
            },
        )

    hits.append(now)
    rate_limit[x_client_id] = hits

    start = int(cursor) if cursor else 0

    end = min(start + limit, TOTAL_ORDERS)

    items = []

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
