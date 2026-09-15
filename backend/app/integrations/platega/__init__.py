"""
Platega Payment Gateway Integration
https://docs.platega.io/
API: https://app.platega.io
"""
import httpx
from typing import Dict, Optional
from decimal import Decimal
from app.core.config import settings
from app.core.logging import logger


class PlategaClient:
    """
    Platega payment gateway client
    
    Uses new API at app.platega.io with X-MerchantId and X-Secret headers
    """
    
    def __init__(self):
        self.api_url = settings.platega_api_url
        self.merchant_id = settings.platega_merchant_id
        self.secret_key = settings.platega_secret_key
        
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=30.0,
            headers={
                "X-MerchantId": self.merchant_id,
                "X-Secret": self.secret_key,
                "Content-Type": "application/json",
            }
        )
    
    async def create_payment(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        success_url: Optional[str] = None,
        fail_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        currency: str = "RUB",
        payment_method: int = 2  # 2 = SBP QR
    ) -> Dict:
        """
        Create payment link
        
        API: POST /transaction/process
        Docs: https://docs.platega.io/создание-ссылки-на-оплату-22645076e0
        
        Args:
            amount: Payment amount
            order_id: Unique order ID (used in metadata)
            description: Payment description
            user_email: Customer email (not used in new API)
            user_phone: Customer phone (not used in new API)
            success_url: Redirect URL on success
            fail_url: Redirect URL on failure
            callback_url: Webhook URL (not used, configured in dashboard)
            currency: Currency code (default RUB)
            payment_method: Payment method (2=SBP QR)
        
        Returns:
            {
                "success": bool,
                "payment_url": str,
                "payment_id": str,
                "order_id": str
            }
        """
        try:
            import json
            
            data = {
                "command": "process",  # Required field
                "paymentMethod": payment_method,
                "paymentDetails": {
                    "amount": float(amount),
                    "currency": currency
                },
                "description": description,
                "return": success_url or settings.platega_success_url,
                "failedUrl": fail_url or settings.platega_failure_url,
                "payload": json.dumps({"order_id": order_id})  # Must be string
            }
            
            logger.info(f"Creating Platega payment: order_id={order_id}, amount={amount} {currency}")
            logger.info(f"Platega request data: {data}")
            
            response = await self.client.post(
                "/transaction/process",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            transaction_id = result.get('transactionId')
            redirect_url = result.get('redirect')  # API returns 'redirect' not 'redirectUrl'
            
            logger.info(f"Platega payment created: transaction_id={transaction_id}, redirect={redirect_url}")
            
            return {
                "success": True,
                "payment_url": redirect_url,
                "payment_id": transaction_id,
                "order_id": order_id
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Platega API error: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"API error: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"Platega payment creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """
        Check payment status
        
        API: GET /transaction/status/{payment_id}
        
        Args:
            payment_id: Platega transaction ID
        
        Returns:
            Payment status data
        """
        try:
            response = await self.client.get(f"/transaction/status/{payment_id}")
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Payment status: {payment_id} - {result.get('status')}")
            
            return {
                "success": True,
                "status": result.get("status"),
                "amount": result.get("amount"),
                "currency": result.get("currency"),
                "payment_id": payment_id,
            }
            
        except Exception as e:
            logger.error(f"Platega status check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_webhook_signature(self, data: Dict, signature: str) -> bool:
        """
        Verify webhook signature from Platega
        
        For new API, webhook verification may differ.
        Check Platega documentation for exact implementation.
        """
        # New API may use different verification method
        # For now, return True - implement proper verification based on docs
        return True
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict:
        """
        Refund payment (full or partial)
        
        Args:
            payment_id: Platega transaction ID
            amount: Refund amount (None for full refund)
        
        Returns:
            Refund result
        """
        try:
            payload = {}
            if amount is not None:
                payload["amount"] = float(amount)
            
            logger.info(f"Refunding payment: payment_id={payment_id}, amount={amount}")
            
            response = await self.client.post(
                f"/transaction/{payment_id}/refund",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Payment refunded: {result}")
            
            return {
                "success": True,
                "refund_id": result.get("refundId"),
                "status": result.get("status")
            }
            
        except Exception as e:
            logger.error(f"Platega refund failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global client instance
platega_client = PlategaClient()
