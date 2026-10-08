from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.warehouses import router as warehouses_router
from app.routers.inventory import router as inventory_router
from app.routers.order import router as order_router
from app.routers.order_assignment import router as order_assignment_router
from app.routers.fulfillment import router as fulfillment_router
from app.routers.returns import router as returns_router
from app.routers.refunds import router as refunds_router
from app.routers.notifications import router as notifications_router
from app.routers.dashboard import router as dashboard_router
from app.routers.audit_logs import router as audit_logs_router

app = FastAPI(
    title="Order Fulfillment & Inventory Management Platform",
    version="1.0.0",
    docs_url="/",
    redoc_url=None,
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "details": exc.errors(),
        },
    )

@app.exception_handler(IntegrityError)
async def integrity_exception_handler(
    request: Request,
    exc: IntegrityError,
):
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "error": "Database integrity error",
            "detail": "The requested operation violates a database constraint.",
        },
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Database error",
            "detail": "A database error occurred while processing the request.",
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred.",
        },
    )

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(warehouses_router)
app.include_router(inventory_router)
app.include_router(order_router)
app.include_router(order_assignment_router)
app.include_router(fulfillment_router)
app.include_router(returns_router)
app.include_router(refunds_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(audit_logs_router)