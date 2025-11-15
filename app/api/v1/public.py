from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models.pricing_plan import PricingPlan
from pydantic import BaseModel, EmailStr

router = APIRouter()


# Schemas
class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: str
    message: str
    api_calls_per_month: str


class PricingPlanResponse(BaseModel):
    id: str
    name: str
    description: str
    api_calls_limit: Optional[int]
    price_per_call: float
    monthly_fee: float
    features: list


# Endpoints
@router.get("/pricing")
async def get_pricing_plans(db: AsyncSession = Depends(get_db)):
    """Get all pricing plans"""
    result = await db.execute(select(PricingPlan))
    plans = result.scalars().all()
    
    if not plans:
        # Return default pricing structure
        return [
            {
                "id": "starter",
                "name": "Starter",
                "description": "Perfect for small projects",
                "api_calls_limit": 50000,
                "price_per_call": 0.001,
                "monthly_fee": 0,
                "features": ["50k API calls/month", "Basic support", "Standard response time"]
            },
            {
                "id": "professional",
                "name": "Professional",
                "description": "For growing businesses",
                "api_calls_limit": 200000,
                "price_per_call": 0.0008,
                "monthly_fee": 99,
                "features": ["200k API calls/month", "Priority support", "Faster response time", "Dedicated account manager"]
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "description": "For large-scale operations",
                "api_calls_limit": None,
                "price_per_call": 0.0005,
                "monthly_fee": 499,
                "features": ["Unlimited API calls", "24/7 support", "Custom SLA", "White-label option", "Dedicated infrastructure"]
            }
        ]
    
    return [
        PricingPlanResponse(
            id=plan.id,
            name=plan.name,
            description=plan.description or "",
            api_calls_limit=plan.api_calls_limit,
            price_per_call=float(plan.price_per_call or 0),
            monthly_fee=float(plan.monthly_fee or 0),
            features=plan.features_json or []
        )
        for plan in plans
    ]


@router.post("/contact")
async def submit_contact_form(form_data: ContactForm):
    """Submit contact form (would typically send email or store in DB)"""
    # In a real implementation, this would:
    # 1. Send email to admin
    # 2. Store in database
    # 3. Trigger notification
    
    return {
        "success": True,
        "message": "Thank you for your inquiry. Our team will contact you soon."
    }


@router.get("/docs/overview")
async def get_api_documentation():
    """Get API documentation overview"""
    return {
        "title": "API Services Platform Documentation",
        "version": "1.0.0",
        "base_url": "/api/v1",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Include your API key in the X-API-Key header for all requests"
        },
        "endpoints": [
            {
                "name": "RC Verification",
                "method": "POST",
                "path": "/rc",
                "description": "Verify vehicle RC details using registration number",
                "request_example": {
                    "reg_no": "TR02ACXXXX"
                },
                "response_time": "< 500ms"
            },
            {
                "name": "Licence Verification",
                "method": "POST",
                "path": "/licence",
                "description": "Verify driving licence details",
                "request_example": {
                    "dl_no": "GJ0520210012345",
                    "dob": "1996-11-15"
                },
                "response_time": "< 500ms"
            },
            {
                "name": "Challan Verification",
                "method": "POST",
                "path": "/challan",
                "description": "Get vehicle challan/violation details",
                "request_example": {
                    "vehicle_no": "UP44BD0599"
                },
                "response_time": "< 500ms"
            }
        ],
        "rate_limits": {
            "default": "100 requests per minute",
            "description": "Rate limits can be customized for enterprise plans"
        },
        "support": {
            "email": "support@apiservices.com",
            "documentation": "/docs",
            "status_page": "/status"
        }
    }

