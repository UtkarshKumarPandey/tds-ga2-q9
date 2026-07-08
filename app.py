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

orders = {}
buckets = {}


class Order(BaseModel):
    item: Optional[str] = "demo"


@app.middleware("http")
async def rate_limiter(request: Request, call_next):

    if request.url.path == "/orders":

        client = request.headers.get("X-Client-Id")

        if client:

            now = time.time()

            hits = buckets.get(client, [])
            hits = [t for t in hits if now - t < WINDOW]

            if len(hits) >= RATE_LIMIT:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "10"},
                )

            hits.append(now)
            buckets[client] = hits

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
    x_client_id: str = Header(..., alias="X-Client-Id"),
    limit: int = 10,
    cursor: str = "0",
):
    try:
        start = int(cursor)
    except:
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
