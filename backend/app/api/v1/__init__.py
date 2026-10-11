from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.students import router as students_router
from app.api.v1.admissions import router as admissions_router
from app.api.v1.admin import router as admin_router
from app.api.v1.tnea import router as tnea_router
from app.api.v1.applications import router as applications_router
from app.api.v1.documents import router as documents_router
from app.api.v1.scrutiny import router as scrutiny_router
from app.api.v1.physical_verification import router as physical_verification_router
from app.api.v1.payments import router as payments_router
from app.api.v1.erp import router as erp_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.timeline import router as timeline_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.chat import router as chat_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.parent import router as parent_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(admissions_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(tnea_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(scrutiny_router)
api_v1_router.include_router(physical_verification_router)
api_v1_router.include_router(payments_router, prefix="/payments")
api_v1_router.include_router(erp_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(timeline_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(onboarding_router)
api_v1_router.include_router(parent_router)

