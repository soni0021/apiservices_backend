"""
WebSocket event definitions and helpers
"""
from typing import Dict, Any
from datetime import datetime


def create_api_call_event(
    user_id: str,
    service_id: str,
    service_name: str,
    api_key_id: str,
    credits_deducted: float,
    credits_before: float,
    credits_after: float,
    response_status: int,
    response_time_ms: int
) -> Dict[str, Any]:
    """Create API call event for WebSocket broadcast"""
    return {
        "type": "api_call",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "user_id": user_id,
            "service_id": service_id,
            "service_name": service_name,
            "api_key_id": api_key_id,
            "credits_deducted": credits_deducted,
            "credits_before": credits_before,
            "credits_after": credits_after,
            "response_status": response_status,
            "response_time_ms": response_time_ms
        }
    }


def create_credit_purchase_event(
    user_id: str,
    transaction_id: str,
    amount_paid: float,
    credits_purchased: float,
    new_balance: float
) -> Dict[str, Any]:
    """Create credit purchase event for WebSocket broadcast"""
    return {
        "type": "credit_purchase",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "user_id": user_id,
            "transaction_id": transaction_id,
            "amount_paid": amount_paid,
            "credits_purchased": credits_purchased,
            "new_balance": new_balance
        }
    }


def create_subscription_event(
    user_id: str,
    service_id: str,
    service_name: str,
    subscription_id: str,
    status: str,
    credits_allocated: float
) -> Dict[str, Any]:
    """Create subscription creation/update event"""
    return {
        "type": "subscription",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "user_id": user_id,
            "service_id": service_id,
            "service_name": service_name,
            "subscription_id": subscription_id,
            "status": status,
            "credits_allocated": credits_allocated
        }
    }


def create_user_registration_event(
    user_id: str,
    email: str,
    full_name: str,
    role: str
) -> Dict[str, Any]:
    """Create new user registration event for admin"""
    return {
        "type": "user_registration",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role
        }
    }


def create_credit_balance_update_event(
    user_id: str,
    total_credits: float,
    credits_used: float,
    credits_remaining: float
) -> Dict[str, Any]:
    """Create credit balance update event"""
    return {
        "type": "credit_balance_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "user_id": user_id,
            "total_credits": total_credits,
            "credits_used": credits_used,
            "credits_remaining": credits_remaining
        }
    }

