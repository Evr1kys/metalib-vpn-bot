"""
Security: Authentication, Authorization, Encryption
"""
import secrets
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
from app.core.logging import logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Data encryption (for sensitive fields like VPN configs)
# CRITICAL: encryption_key must be a valid 32-byte base64-encoded key
def _get_fernet():
    """Get Fernet instance with validated encryption key"""
    try:
        key = settings.encryption_key.encode()
        if len(key) != 44:  # Fernet key is 32 bytes base64 = 44 chars
            raise ValueError(f"Invalid encryption key length: {len(key)}. Expected 44 characters (base64-encoded 32 bytes)")
        
        # Validate key format
        fernet = Fernet(key)
        # Test encryption/decryption
        test_data = fernet.encrypt(b"test")
        fernet.decrypt(test_data)
        return fernet
    except Exception as e:
        logger.critical(f"ENCRYPTION KEY ERROR: {e}")
        logger.critical("To generate a valid key, run: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        raise RuntimeError(f"Invalid ENCRYPTION_KEY configuration: {e}")

fernet = _get_fernet()


# ===== Password Hashing =====

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ===== JWT Tokens =====

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# ===== Data Encryption =====

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data (e.g., VPN configs, SSH keys)"""
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return fernet.decrypt(encrypted_data.encode()).decode()


# ===== Webhook Signature Verification =====

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature (HMAC-SHA256)
    
    Args:
        payload: Raw request body
        signature: Signature from header (e.g., X-Signature)
        secret: Secret key for HMAC
    
    Returns:
        True if signature is valid
    """
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def generate_webhook_signature(payload: str, secret: str) -> str:
    """Generate webhook signature"""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


# ===== Signed URLs for VPN Keys =====

def generate_signed_vpn_url(key_id: str, expires_in_hours: int = 24) -> str:
    """
    Generate a time-limited signed URL token for VPN key access
    
    Args:
        key_id: VPN account UUID
        expires_in_hours: How long the URL is valid (default 24 hours)
    
    Returns:
        Signed token string (base64 encoded)
    """
    from app.core.config import settings
    
    expires_at = int((datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp())
    message = f"{key_id}:{expires_at}"
    
    signature = hmac.new(
        settings.secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # Use first 16 chars for shorter URL
    
    # Format: key_id.expires_at.signature
    token = f"{key_id}.{expires_at}.{signature}"
    return base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')


def verify_signed_vpn_url(token: str) -> Optional[str]:
    """
    Verify a signed VPN URL token and return the key_id if valid
    
    Args:
        token: Signed token string
    
    Returns:
        key_id if valid, None if expired or invalid
    """
    from app.core.config import settings
    
    try:
        # Add padding back to base64
        padding = 4 - len(token) % 4
        if padding != 4:
            token += '=' * padding
        
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.split('.')
        
        if len(parts) != 3:
            return None
        
        key_id, expires_at_str, signature = parts
        expires_at = int(expires_at_str)
        
        # Check expiration
        if datetime.utcnow().timestamp() > expires_at:
            return None
        
        # Verify signature
        message = f"{key_id}:{expires_at_str}"
        expected_signature = hmac.new(
            settings.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        return key_id
        
    except Exception:
        return None


# ===== Token Generation =====

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def generate_device_binding_token() -> str:
    """Generate short device binding token (8 characters, alphanumeric)"""
    # Generate 6-character token (easier for users to type)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # excluding ambiguous chars
    return ''.join(secrets.choice(alphabet) for _ in range(6))


# ===== API Key Verification =====

def verify_api_key(api_key: str, expected_key: str) -> bool:
    """Verify API key (constant-time comparison)"""
    return hmac.compare_digest(api_key, expected_key)


# ===== Agent Authentication =====

def create_agent_signature(server_id: str, timestamp: str, secret: str) -> str:
    """Create signature for agent communication"""
    message = f"{server_id}:{timestamp}"
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_agent_signature(
    server_id: str,
    timestamp: str,
    signature: str,
    secret: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Verify agent signature with timestamp validation
    
    Args:
        server_id: Server identifier
        timestamp: Unix timestamp as string
        signature: HMAC signature
        secret: Shared secret
        max_age_seconds: Maximum age of request (replay protection)
    
    Returns:
        True if signature is valid and not expired
    """
    try:
        # Check timestamp freshness
        request_time = datetime.fromtimestamp(int(timestamp))
        now = datetime.utcnow()
        
        if abs((now - request_time).total_seconds()) > max_age_seconds:
            return False
        
        # Verify signature
        expected_signature = create_agent_signature(server_id, timestamp, secret)
        return hmac.compare_digest(signature, expected_signature)
        
    except (ValueError, OverflowError):
        return False
