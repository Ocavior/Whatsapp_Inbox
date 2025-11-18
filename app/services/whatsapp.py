import requests
import json
import time
from typing import Dict, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import *
from app.utils.logger import logger
from app.services.mongodb_rate_limiter import MongoDBRateLimiter
from app.services.mongodb_cache import MongoDBCache


class WhatsAppService:
    """WhatsApp Business API service"""
    
    def __init__(self):
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        self.rate_limiter = MongoDBRateLimiter(
            max_requests=80,  # WhatsApp limit
            window_seconds=1
        )
        self.cache = MongoDBCache()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError
        ))
    )
    async def send_text_message(self, to: str, message: str) -> Dict:
        """Send text message with retry logic"""
        
        # Wait for rate limit
        if not await self.rate_limiter.acquire("whatsapp_api"):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": 429
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.normalize_phone_number(to),
            "type": "text",
            "text": {"body": message}
        }
        
        return await self._make_request(payload)
    
    async def send_template_message(self, to: str, template_name: str, 
                                  parameters: List[Dict] = None,
                                  language_code: str = "en_US") -> Dict:
        """Send template message"""
        
        if not await self.rate_limiter.acquire("whatsapp_api"):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": 429
            }
        
        template_data = {
            "name": template_name,
            "language": {"code": language_code}
        }
        
        if parameters:
            template_data["components"] = [{
                "type": "body",
                "parameters": parameters
            }]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": self.normalize_phone_number(to),
            "type": "template",
            "template": template_data
        }
        
        return await self._make_request(payload)
    
    async def send_media_message(self, to: str, media_type: str, 
                               media_url: str = None, media_id: str = None,
                               caption: str = None) -> Dict:
        """Send media message (image, video, audio, document)"""
        
        if not await self.rate_limiter.acquire("whatsapp_api"):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": 429
            }
        
        if not media_url and not media_id:
            return {
                "success": False,
                "error": "Either media_url or media_id must be provided"
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": self.normalize_phone_number(to),
            "type": media_type
        }
        
        if media_type == "image":
            payload["image"] = {"link" if media_url else "id": media_url or media_id}
            if caption:
                payload["image"]["caption"] = caption
        elif media_type == "video":
            payload["video"] = {"link" if media_url else "id": media_url or media_id}
            if caption:
                payload["video"]["caption"] = caption
        elif media_type == "audio":
            payload["audio"] = {"link" if media_url else "id": media_url or media_id}
        elif media_type == "document":
            payload["document"] = {"link" if media_url else "id": media_url or media_id}
            if caption:
                payload["document"]["caption"] = caption
        
        return await self._make_request(payload)
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    async def _make_request(self, payload: Dict) -> Dict:
        """Make API request to WhatsApp Business API"""
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                time.sleep(retry_after)
                raise requests.exceptions.RetryError("Rate limited")
            
            response_data = response.json()
            
            if response.status_code == 200:
                message_id = response_data.get("messages", [{}])[0].get("id")
                logger.info(f"Message sent successfully, ID: {message_id}")
                return {
                    "success": True,
                    "message_id": message_id,
                    "error": None
                }
            else:
                error = response_data.get("error", {})
                error_msg = error.get("message", "Unknown error")
                error_code = error.get("code")
                
                logger.error(f"API error {error_code}: {error_msg}")
                return {
                    "success": False,
                    "message_id": None,
                    "error": error_msg,
                    "error_code": error_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return {
                "success": False,
                "message_id": None,
                "error": "Request timeout"
            }
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return {
                "success": False,
                "message_id": None,
                "error": "Connection error"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "message_id": None,
                "error": str(e)
            }
    
    def normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number for WhatsApp API"""
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone))
        
        # Ensure it has country code
        if len(cleaned) == 10:  # Assume India if no country code
            cleaned = '91' + cleaned
        
        return cleaned
    
    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature from Meta"""
        import hmac
        import hashlib
        
        if not signature or not WHATSAPP_APP_SECRET:
            return False
        
        expected_signature = hmac.new(
            WHATSAPP_APP_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)