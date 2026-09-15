"""
Platega Payment Gateway Integration

API Documentation: https://docs.platega.io
Base URL: https://app.platega.io
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import httpx
from app.core.config import settings
from app.core.logging import logger


class PlategaClient:
    """
    Client for Platega Payment Gateway
    
    Документация: https://docs.platega.io
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
        currency: str,
        order_id: str,
        description: str,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        success_url: Optional[str] = None,
        failure_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        payment_method: int = 2  # 2 = SBP QR
    ) -> Dict[str, Any]:
        """
        Create payment transaction
        
        API: POST /transaction/process
        Docs: https://docs.platega.io/создание-ссылки-на-оплату-22645076e0
        
        Args:
            amount: Payment amount
            currency: Currency code (RUB, USD, etc.)
            order_id: Unique order ID
            description: Payment description
            customer_email: Customer email (optional)
            customer_phone: Customer phone (optional)
            success_url: Success redirect URL
            failure_url: Failure redirect URL
            metadata: Additional info
            payment_method: Payment method ID (2=SBPQR, see docs)
        
        Returns:
            Payment data with external_id and payment_url
        """
        try:
            data = {
                "paymentMethod": payment_method,
                "paymentDetails": {
                    "amount": float(amount),
                    "currency": currency
                },
                "description": description,
                "return": success_url or settings.platega_success_url,
                "failedUrl": failure_url or settings.platega_failure_url,
            }
            
            if metadata:
                data["payload"] = metadata
            
            logger.info(f"Creating Platega payment: {order_id}, amount: {amount} {currency}")
            
            response = await self.client.post(
                "/transaction/process",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            transaction_id = result.get('transactionId')
            redirect_url = result.get('redirectUrl')
            
            logger.info(f"Payment created: transaction_id={transaction_id}")
            
            # Convert to expected format for payment_service
            return {
                "external_id": transaction_id,
                "payment_url": redirect_url,
                "status": "pending"
            }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Platega API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            raise
    
    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get payment status
        
        API: GET /transaction/status/{transaction_id}
        Docs: https://docs.platega.io/проверка-статуса-оплаты-платежа-22645077e0
        
        Args:
            transaction_id: Transaction ID from create_payment
        
        Returns:
            Payment status data
        """
        try:
            response = await self.client.get(f"/transaction/status/{transaction_id}")
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Payment status: {transaction_id} - {result.get('status')}")
            
            return result
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get payment status: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Failed to get payment status: {e}")
            raise
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment
        
        Args:
            transaction_id: Platega transaction ID
            amount: Refund amount (null = full refund)
            reason: Refund reason
        
        Returns:
            Refund data
        """
        try:
            payload = {}
            
            if amount is not None:
                payload["amount"] = float(amount)
            
            if reason:
                payload["reason"] = reason
            
            logger.info(f"Refunding payment: transaction_id={transaction_id}, amount={amount}")
            
            response = await self.client.post(
                f"/transaction/{transaction_id}/refund",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Payment refunded: {data}")
            
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Platega API error: {e}")
            raise
    
    @staticmethod
    def parse_webhook_event(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse webhook event data
        
        Args:
            data: Webhook JSON payload
        
        Returns:
            Parsed event data
        
        Possible statuses:
        - success: Payment successful
        - failed: Payment failed
        - refunded: Payment refunded
        """
        transaction_id = data.get("transactionId")
        status = data.get("status")
        
        logger.info(f"Webhook event: transaction_id={transaction_id}, status={status}")
        
        return {
            "transaction_id": transaction_id,
            "status": status,
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "payload": data.get("payload"),
            "raw_data": data,
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_platega_client: Optional[PlategaClient] = None


def get_platega_client() -> PlategaClient:
    """Get Platega client instance"""
    global _platega_client
    
    if _platega_client is None:
        _platega_client = PlategaClient()
    
    return _platega_client
