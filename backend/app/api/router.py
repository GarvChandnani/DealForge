"""
DealForge Backend — Root API Router.

Mounts all versioned sub-routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1 import auth, health, deals, contacts, crm, mandate_generations, investors, matching, data_rooms, due_diligence, compliance, documents, transactions

api_router = APIRouter()

# Mount v1 routes
api_router.include_router(health.router, prefix="/api/v1")
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(deals.router, prefix="/api/v1")
api_router.include_router(contacts.router, prefix="/api/v1")
api_router.include_router(crm.router, prefix="/api/v1")
api_router.include_router(mandate_generations.router, prefix="/api/v1")
api_router.include_router(investors.router, prefix="/api/v1")
api_router.include_router(matching.router, prefix="/api/v1")
api_router.include_router(data_rooms.router, prefix="/api/v1")
api_router.include_router(due_diligence.router, prefix="/api/v1")
api_router.include_router(compliance.router, prefix="/api/v1")
api_router.include_router(documents.router, prefix="/api/v1")
api_router.include_router(transactions.router, prefix="/api/v1")
