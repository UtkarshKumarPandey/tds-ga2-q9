from fastapi import FastAPI, Header, Request, Response
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 51
RATE_LIMIT = 15
WINDOW = 10

orders_by_key = {}
rate_store = {}


class Order(BaseModel):
    item: Optional[str] = "demo"


@app.middleware("http")
async def rate_limit(request: Request, call_next):

    if request.method == "GET" and request.url.path == "/orders":
        client = request.headers.get("X-Client-Id")

        if client:
            now = time.time()

            hits = rate_store.get(client, [])
            hits = [t for t in hits if now - t < WINDOW]

            if len(hits) >= RATE_LIMIT:
                retry_after = max(1, int(WINDOW - (now - hits[0])))

                return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after),
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                },
            )

            hits.append(now)
            rate_store[client] = hits

    return await call_next(request)


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/orders")
def create_order(
    order: Order,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    response.status_code = 201

    if idempotency_key in orders_by_key:
        return orders_by_key[idempotency_key]

    obj = {
        "id": str(uuid.uuid4()),
        "item": order.item,
    }

    orders_by_key[idempotency_key] = obj

    return obj


@app.get("/orders")
def list_orders(
    limit: int = 10,
    cursor: str = "0",
):
    try:
        start = int(cursor)
    except Exception:
        start = 0

    if limit < 1:
        limit = 1

    end = min(start + limit, TOTAL_ORDERS)

    items = [{"id": i} for i in range(start + 1, end + 1)]

    next_cursor = None
    if end < TOTAL_ORDERS:
        next_cursor = str(end)

    return {
        "items": items,
        "next_cursor": next_cursor,
    }
