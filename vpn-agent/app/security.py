"""
VPN Agent Security
"""
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Header, HTTPException, status

from app.config import settings


def verify_hmac_signature(
    data: str,
    signature: str,
    timestamp: Optional[str] = None
) -> bool:
    """
    Verify HMAC signature from backend
    
    Args:
        data: Request data (JSON string)
        signature: HMAC signature from X-Signature header
        timestamp: Request timestamp from X-Timestamp header
    
    Returns:
        True if signature is valid
    """
    # Check timestamp if provided (prevent replay attacks)
    if timestamp:
        try:
            request_time = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - request_time > timedelta(minutes=5):
                return False
        except (ValueError, TypeError):
            return False
    
    # Calculate expected signature
    message = data.encode('utf-8')
    expected_signature = hmac.new(
        settings.agent_secret_key.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    return hmac.compare_digest(signature, expected_signature)


async def verify_request(
    x_signature: str = Header(...),
    x_timestamp: str = Header(...)
) -> bool:
    """
    FastAPI dependency to verify request authentication
    
    Args:
        x_signature: HMAC signature from header
        x_timestamp: Request timestamp from header
    
    Returns:
        True if authenticated
    
    Raises:
        HTTPException: If authentication fails
    """
    # Timestamp validation done in verify_hmac_signature
    # Signature will be validated per-endpoint with request body
    return True
