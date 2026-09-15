"""
VPN Provisioning API endpoints

Features:
- Rate limiting on key access endpoints
- QR code generation
- VPN key pages with instructions
- Time-limited signed URLs for security
"""
from typing import Optional, Union
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import base64
import qrcode
from io import BytesIO


def validate_uuid(value: str) -> bool:
    """Validate if string is a valid UUID"""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False

from app.api.deps import get_db, get_current_admin
from app.services.xray_service import XrayService
from app.models import AdminUser, VPNAccount, Subscription, VPNAccountStatus
from app.core.rate_limit import limiter, RateLimitConfig
from app.core.security import generate_signed_vpn_url, verify_signed_vpn_url

router = APIRouter()


def get_connection_string(config: Union[str, dict]) -> str:
    """Extract connection string from config (supports both dict and string formats)"""
    import json
    
    # If it's a string, try to parse as JSON
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except (json.JSONDecodeError, TypeError):
            return config
    
    # If it's a dict, get connection_string
    if isinstance(config, dict):
        return config.get("connection_string", str(config))
    
    return str(config)


class VPNProvisionRequest(BaseModel):
    """VPN provision request"""
    subscription_id: str
    server_id: str
    email: Optional[str] = None


class VPNConfigResponse(BaseModel):
    """VPN config response"""
    id: str
    subscription_id: str
    server_id: str
    protocol: str
    username: str
    config: str
    status: str
    created_at: str


# ============= PUBLIC ENDPOINTS (no auth) =============

@router.get("/key/{key_token}/qr")
@limiter.limit("60/minute")
@limiter.limit("500/hour")
async def get_vpn_key_qr(
    request: Request,
    key_token: str,
    sig: Optional[str] = Query(None, description="Signed URL token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get QR code image for VPN key
    Returns PNG image of QR code
    
    Supports both direct UUID access and signed URL tokens for security.
    """
    # Try signed URL first if provided
    actual_key_id = key_token
    if sig:
        verified_id = verify_signed_vpn_url(sig)
        if verified_id:
            actual_key_id = verified_id
        else:
            raise HTTPException(status_code=403, detail="Expired or invalid signed URL")
    
    # Validate UUID format
    if not validate_uuid(actual_key_id):
        raise HTTPException(status_code=404, detail="Invalid key format")
    
    stmt = select(VPNAccount).where(
        VPNAccount.id == actual_key_id,
        VPNAccount.status == VPNAccountStatus.ACTIVE
    )
    result = await db.execute(stmt)
    vpn_account = result.scalars().first()
    
    if not vpn_account:
        raise HTTPException(status_code=404, detail="Key not found or expired")
    
    connection_string = get_connection_string(vpn_account.config)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(connection_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.get("/key/{key_token}")
@limiter.limit("60/minute")
@limiter.limit("500/hour")
async def get_vpn_key_public(
    request: Request,
    key_token: str,
    sig: Optional[str] = Query(None, description="Signed URL token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get VPN key by token (public, no auth)
    
    Token is the VPN account UUID or a signed URL token.
    Returns config for import into VPN client.
    """
    # Try signed URL first if provided
    actual_key_id = key_token
    if sig:
        verified_id = verify_signed_vpn_url(sig)
        if verified_id:
            actual_key_id = verified_id
        else:
            raise HTTPException(status_code=403, detail="Expired or invalid signed URL")
    
    # Validate UUID format
    if not validate_uuid(actual_key_id):
        raise HTTPException(status_code=404, detail="Invalid key format")
    
    stmt = select(VPNAccount).where(
        VPNAccount.id == actual_key_id,
        VPNAccount.status == VPNAccountStatus.ACTIVE
    )
    result = await db.execute(stmt)
    vpn_account = result.scalars().first()
    
    if not vpn_account:
        raise HTTPException(status_code=404, detail="Key not found or expired")
    
    return {
        "config": get_connection_string(vpn_account.config),
        "protocol": vpn_account.protocol,
        "expires_at": None  # Can be added based on subscription
    }

@router.get("/key/{key_token}/page", response_class=HTMLResponse)
@limiter.limit("60/minute")
@limiter.limit("500/hour")
async def get_vpn_key_page(
    request: Request,
    key_token: str,
    sig: Optional[str] = Query(None, description="Signed URL token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get VPN key page with instructions (public)
    
    Beautiful page with QR code and instructions.
    Supports signed URL tokens for time-limited access.
    """
    # Try signed URL first if provided
    actual_key_id = key_token
    if sig:
        verified_id = verify_signed_vpn_url(sig)
        if verified_id:
            actual_key_id = verified_id
        else:
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html><head><title>Ссылка истекла</title>
            <style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;background:#0f0f1a;color:white;flex-direction:column;}</style>
            </head><body><h1>⏰ Срок действия ссылки истёк</h1><p>Запросите новую ссылку в боте</p></body></html>
            """, status_code=403)
    
    # Validate UUID format
    if not validate_uuid(actual_key_id):
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html><head><title>Ключ не найден</title></head>
        <body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;">
        <h1>❌ Неверный формат ключа</h1>
        </body></html>
        """, status_code=404)
    
    stmt = select(VPNAccount).where(
        VPNAccount.id == actual_key_id,
        VPNAccount.status == VPNAccountStatus.ACTIVE
    )
    result = await db.execute(stmt)
    vpn_account = result.scalars().first()
    
    if not vpn_account:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html><head><title>Ключ не найден</title>
        <style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;background:#0f0f1a;color:white;}</style>
        </head><body><h1>Ключ не найден или истёк срок действия</h1></body></html>
        """, status_code=404)
    
    # Get connection string and generate QR code
    connection_string = get_connection_string(vpn_account.config)
    qr_data = generate_qr_base64(connection_string)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MetaLib VPN - Ваш ключ</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
                min-height: 100vh;
                color: white;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                font-size: 2.5rem;
                font-weight: bold;
                background: linear-gradient(135deg, #8b5cf6, #ec4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .card {{
                background: rgba(26, 26, 46, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }}
            .qr-container {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .qr-container img {{
                border-radius: 15px;
                background: white;
                padding: 15px;
            }}
            .key-box {{
                background: #0f0f1a;
                border-radius: 10px;
                padding: 15px;
                word-break: break-all;
                font-family: monospace;
                font-size: 0.75rem;
                color: #a0a0b0;
                margin: 15px 0;
            }}
            .copy-btn {{
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #8b5cf6, #ec4899);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            .copy-btn:hover {{ transform: scale(1.02); }}
            .copy-btn:active {{ transform: scale(0.98); }}
            h2 {{
                color: #8b5cf6;
                margin-bottom: 15px;
                font-size: 1.3rem;
            }}
            .step {{
                display: flex;
                gap: 15px;
                margin-bottom: 15px;
                align-items: flex-start;
            }}
            .step-num {{
                background: linear-gradient(135deg, #8b5cf6, #ec4899);
                min-width: 30px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }}
            .step-text {{ flex: 1; color: #cbd5e1; }}
            .app-links {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 20px;
            }}
            .app-link {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                padding: 12px;
                background: rgba(139, 92, 246, 0.2);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 10px;
                color: white;
                text-decoration: none;
                transition: background 0.2s;
            }}
            .app-link:hover {{ background: rgba(139, 92, 246, 0.4); }}
            .success-msg {{
                display: none;
                background: rgba(34, 197, 94, 0.2);
                border: 1px solid rgba(34, 197, 94, 0.5);
                padding: 10px;
                border-radius: 8px;
                text-align: center;
                color: #22c55e;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🛡️ MetaLib VPN</div>
                <p style="color: #a0a0b0; margin-top: 10px;">Ваш персональный ключ доступа</p>
            </div>

            <div class="card">
                <h2>📱 Отсканируйте QR-код</h2>
                <div class="qr-container">
                    <img src="data:image/png;base64,{qr_data}" alt="VPN QR Code" width="200" height="200">
                </div>
                <p style="text-align: center; color: #a0a0b0; font-size: 0.9rem;">
                    Откройте приложение VPN и отсканируйте QR-код
                </p>
            </div>

            <div class="card">
                <h2>🔑 Или скопируйте ключ</h2>
                <div class="key-box" id="vpnKey">{connection_string}</div>
                <button class="copy-btn" onclick="copyKey()">📋 Скопировать ключ</button>
                <div class="success-msg" id="successMsg">✅ Ключ скопирован!</div>
            </div>

            <div class="card">
                <h2>📲 Как подключиться</h2>
                <div class="step">
                    <div class="step-num">1</div>
                    <div class="step-text">Скачайте приложение для вашего устройства</div>
                </div>
                <div class="step">
                    <div class="step-num">2</div>
                    <div class="step-text">Отсканируйте QR-код или вставьте ключ</div>
                </div>
                <div class="step">
                    <div class="step-num">3</div>
                    <div class="step-text">Подключитесь и пользуйтесь интернетом без ограничений!</div>
                </div>

                <div class="app-links">
                    <a href="https://apps.apple.com/app/streisand/id6450534064" class="app-link" target="_blank">
                        🍎 iOS
                    </a>
                    <a href="https://play.google.com/store/apps/details?id=app.hiddify.com" class="app-link" target="_blank">
                        🤖 Android
                    </a>
                    <a href="https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532" class="app-link" target="_blank">
                        💻 macOS
                    </a>
                    <a href="https://github.com/hiddify/hiddify-next/releases" class="app-link" target="_blank">
                        🖥️ Windows
                    </a>
                </div>
            </div>

            <div class="card" style="text-align: center;">
                <p style="color: #a0a0b0;">
                    Нужна помощь? Напишите нам в <a href="https://t.me/metalib_support" style="color: #8b5cf6;">Telegram</a>
                </p>
            </div>
        </div>

        <script>
        function copyKey() {{
            const key = document.getElementById('vpnKey').textContent;
            navigator.clipboard.writeText(key).then(() => {{
                document.getElementById('successMsg').style.display = 'block';
                setTimeout(() => {{
                    document.getElementById('successMsg').style.display = 'none';
                }}, 2000);
            }});
        }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)


def generate_qr_base64(data: str) -> str:
    """Generate QR code as base64 string"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception:
        # Return empty placeholder if qrcode not available
        return ""


# ============= ADMIN ENDPOINTS (require auth) =============


@router.post("/provision", response_model=VPNConfigResponse)
async def provision_vpn_account(
    request: VPNProvisionRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Provision VPN account for subscription
    
    Creates VLESS account in Xray and returns config URI
    """
    xray_service = XrayService(db)
    
    try:
        vpn_account = await xray_service.generate_vless_account(
            subscription_id=request.subscription_id,
            server_id=request.server_id,
            email=request.email
        )
        
        return VPNConfigResponse(
            id=str(vpn_account.id),
            subscription_id=str(vpn_account.subscription_id),
            server_id=str(vpn_account.server_id),
            protocol=vpn_account.protocol,
            username=vpn_account.username,
            config=vpn_account.config,
            status=vpn_account.status,
            created_at=vpn_account.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to provision VPN: {str(e)}")


@router.delete("/{vpn_account_id}")
async def revoke_vpn_account(
    vpn_account_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Revoke VPN account
    
    Removes client from Xray config
    """
    xray_service = XrayService(db)
    
    success = await xray_service.revoke_account(vpn_account_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke VPN account")
    
    return {"success": True, "message": "VPN account revoked"}


@router.get("/{subscription_id}/config")
async def get_vpn_config(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get VPN config for subscription
    
    Returns VLESS URI for client import
    """
    from sqlalchemy import select
    
    stmt = select(VPNAccount).where(
        VPNAccount.subscription_id == subscription_id,
        VPNAccount.status == "active"
    )
    result = await db.execute(stmt)
    vpn_account = result.scalars().first()
    
    if not vpn_account:
        raise HTTPException(status_code=404, detail="VPN account not found")
    
    return {
        "config": vpn_account.config,
        "protocol": vpn_account.protocol,
        "server_id": str(vpn_account.server_id),
        "created_at": vpn_account.created_at.isoformat()
    }


@router.post("/generate-signed-url/{vpn_account_id}")
async def generate_vpn_signed_url(
    vpn_account_id: str,
    expires_hours: int = Query(24, ge=1, le=168, description="Hours until expiration (1-168)"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Generate a time-limited signed URL for VPN key access
    
    Creates a secure, expiring URL that can be shared safely.
    Max expiration: 7 days (168 hours)
    """
    # Verify VPN account exists
    stmt = select(VPNAccount).where(VPNAccount.id == vpn_account_id)
    result = await db.execute(stmt)
    vpn_account = result.scalars().first()
    
    if not vpn_account:
        raise HTTPException(status_code=404, detail="VPN account not found")
    
    signed_token = generate_signed_vpn_url(vpn_account_id, expires_hours)
    
    base_url = "https://metalib.xyz"
    
    return {
        "signed_url": f"{base_url}/{vpn_account_id}?sig={signed_token}",
        "qr_url": f"{base_url}/api/v1/vpn/key/{vpn_account_id}/qr?sig={signed_token}",
        "page_url": f"{base_url}/api/v1/vpn/key/{vpn_account_id}/page?sig={signed_token}",
        "expires_in_hours": expires_hours,
        "token": signed_token
    }


@router.get("/server/{server_id}/clients")
async def get_server_clients(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get all clients on Xray server
    
    Returns list of UUIDs and emails from Xray config
    """
    xray_service = XrayService(db)
    
    clients = await xray_service.get_server_clients(server_id)
    
    return {
        "server_id": server_id,
        "clients": clients,
        "total": len(clients)
    }
