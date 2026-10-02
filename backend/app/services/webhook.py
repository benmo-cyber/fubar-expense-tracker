import httpx
import hmac
import hashlib
import json
from typing import Dict, Any
from app.core.config import settings


class WebhookService:
    def __init__(self):
        self.enabled = settings.WEBHOOK_ENABLED
        self.webhook_url = settings.WEBHOOK_URL
        self.webhook_secret = settings.WEBHOOK_SECRET
    
    def _generate_signature(self, payload: str) -> str:
        if not self.webhook_secret:
            return ""
        
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def send_webhook(self, event_type: str, data: Dict[str, Any]) -> bool:
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            payload = {
                "event": event_type,
                "data": data
            }
            payload_json = json.dumps(payload)
            
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event_type
            }
            
            if self.webhook_secret:
                headers["X-Webhook-Signature"] = self._generate_signature(payload_json)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    content=payload_json,
                    headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Webhook delivery failed: {str(e)}")
            return False
    
    async def notify_expense_approved(self, expense_data: Dict[str, Any]) -> bool:
        return await self.send_webhook("expense.approved", expense_data)
    
    async def notify_expense_rejected(self, expense_data: Dict[str, Any]) -> bool:
        return await self.send_webhook("expense.rejected", expense_data)


webhook_service = WebhookService()
