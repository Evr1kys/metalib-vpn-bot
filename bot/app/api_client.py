"""
API Client for backend communication
"""
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings


class APIClient:
    """Backend API client"""
    
    def __init__(self):
        self.base_url = settings.api_base_url.rstrip("/")
        self.token = settings.bot_api_token
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "X-Bot-Token": self.token,  # Bot authentication token
                "Content-Type": "application/json",
            }
        )
    
    # Generic HTTP methods
    async def get(self, path: str, telegram_id: int = None, **kwargs) -> Dict[str, Any]:
        """Generic GET request"""
        url = f"/api/v1{path}" if not path.startswith("/api/") else path
        # Remove trailing slash to avoid 307 redirect
        url = url.rstrip("/")
        params = kwargs.pop("params", {})
        if telegram_id:
            params["telegram_id"] = telegram_id
        response = await self.client.get(url, params=params, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def post(self, path: str, json: Dict[str, Any] = None, telegram_id: int = None, **kwargs) -> Dict[str, Any]:
        """Generic POST request"""
        url = f"/api/v1{path}" if not path.startswith("/api/") else path
        # Remove trailing slash to avoid 307 redirects
        url = url.rstrip("/")
        params = kwargs.pop("params", {})
        if telegram_id:
            params["telegram_id"] = telegram_id
        response = await self.client.post(url, json=json, params=params, follow_redirects=True, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def delete(self, path: str, telegram_id: int = None, **kwargs) -> Dict[str, Any]:
        """Generic DELETE request"""
        url = f"/api/v1{path}" if not path.startswith("/api/") else path
        url = url.rstrip("/")
        params = kwargs.pop("params", {})
        if telegram_id:
            params["telegram_id"] = telegram_id
        response = await self.client.delete(url, params=params, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # Users
    async def create_or_get_user(self, telegram_id: int, **kwargs) -> Dict[str, Any]:
        """Create or get user"""
        response = await self.client.post(
            "/api/v1/users",
            json={"telegram_id": telegram_id, **kwargs},
            follow_redirects=True
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user(self, telegram_id: int) -> Dict[str, Any]:
        """Get user by telegram ID"""
        response = await self.client.get(f"/api/v1/users/{telegram_id}")
        response.raise_for_status()
        return response.json()
    
    # Plans
    async def get_plans(self) -> List[Dict[str, Any]]:
        """Get all plans"""
        response = await self.client.get("/api/v1/plans", follow_redirects=True)
        response.raise_for_status()
        return response.json()
    
    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        """Get plan by ID"""
        response = await self.client.get(f"/api/v1/plans/{plan_id}")
        response.raise_for_status()
        return response.json()
    
    # Subscriptions
    async def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user subscriptions"""
        response = await self.client.get(f"/api/v1/subscriptions/user/{user_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_active_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription"""
        response = await self.client.get(f"/api/v1/subscriptions/user/{user_id}/active")
        response.raise_for_status()
        return response.json()
    
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel subscription"""
        response = await self.client.post(f"/api/v1/subscriptions/{subscription_id}/cancel")
        response.raise_for_status()
        return response.json()
    
    async def provision_vpn(self, subscription_id: str) -> Dict[str, Any]:
        """Provision VPN access for subscription"""
        response = await self.client.post(f"/api/v1/subscriptions/{subscription_id}/provision-vpn")
        response.raise_for_status()
        return response.json()
    
    async def renew_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Create payment for subscription renewal"""
        response = await self.client.post(f"/api/v1/subscriptions/{subscription_id}/renew")
        response.raise_for_status()
        return response.json()
    
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription by ID"""
        response = await self.client.get(f"/api/v1/subscriptions/{subscription_id}")
        response.raise_for_status()
        return response.json()
    
    # Payments
    async def create_payment(
        self,
        user_id: str,
        plan_id: str,
        promo_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create payment"""
        response = await self.client.post(
            "/api/v1/payments",
            json={
                "user_id": user_id,
                "plan_id": plan_id,
                "promo_code": promo_code,
            },
            follow_redirects=True
        )
        response.raise_for_status()
        return response.json()
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment"""
        response = await self.client.get(f"/api/v1/payments/{payment_id}")
        response.raise_for_status()
        return response.json()
    
    # Devices
    async def generate_device_token(self, subscription_id: str) -> Dict[str, Any]:
        """Generate device binding token"""
        response = await self.client.post(
            "/api/v1/devices/generate-token",
            params={"subscription_id": subscription_id}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_devices(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Get subscription devices"""
        response = await self.client.get(f"/api/v1/devices/subscription/{subscription_id}")
        response.raise_for_status()
        return response.json()
    
    async def unbind_device(self, device_id: str) -> Dict[str, Any]:
        """Unbind device"""
        response = await self.client.delete(f"/api/v1/devices/{device_id}")
        response.raise_for_status()
        return response.json()
    
    # Referrals
    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get referral stats for user"""
        return await self.get("/referrals/me", telegram_id=telegram_id)
    
    async def get_referrals_list(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Get list of user's referrals"""
        return await self.get("/referrals/list", telegram_id=telegram_id)
    
    async def get_referral_status(self) -> Dict[str, Any]:
        """Get referral program status"""
        return await self.get("/referrals/status")
    
    async def close(self):
        """Close client"""
        await self.client.aclose()


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get API client instance"""
    global _api_client
    
    if _api_client is None:
        _api_client = APIClient()
    
    return _api_client
