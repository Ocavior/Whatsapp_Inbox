import asyncio
import csv
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable
from bson import ObjectId
from app.database.mongodb import db
from app.services.whatsapp import WhatsAppService
from app.utils.logger import logger


class BulkMessageSender:
    """Service for sending bulk messages"""
    
    def __init__(self, whatsapp_service: WhatsAppService):
        self.whatsapp_service = whatsapp_service
    
    async def send_bulk_messages(self, contacts: List[Dict], message_template: str,
                               campaign_name: str, delay: float = 1.0,
                               progress_callback: Optional[Callable] = None) -> Dict:
        """Send bulk messages with progress tracking"""
        
        campaign_id = ObjectId()
        total = len(contacts)
        successful = []
        failed = []
        
        # Create campaign record
        await self._create_campaign(campaign_id, campaign_name, total)
        
        for index, contact in enumerate(contacts, 1):
            try:
                phone = contact.get('phone', '').strip()
                if not phone:
                    logger.warning(f"Skipping contact {index}: No phone number")
                    failed.append({
                        **contact,
                        "error": "No phone number"
                    })
                    continue
                
                # Personalize message
                message = self._personalize_message(message_template, contact)
                
                # Send message
                result = await self.whatsapp_service.send_text_message(phone, message)
                
                # Save message to database
                if result['success']:
                    message_data = {
                        "user_id": phone,
                        "direction": "outbound",
                        "message_type": "text",
                        "body": message,
                        "timestamp": datetime.utcnow(),
                        "status": "sent",
                        "message_id": result['message_id'],
                        "campaign_id": campaign_id
                    }
                    
                    await db.db.messages.insert_one(message_data)
                    successful.append(contact)
                    
                else:
                    # Save failed message
                    message_data = {
                        "user_id": phone,
                        "direction": "outbound",
                        "message_type": "text",
                        "body": message,
                        "timestamp": datetime.utcnow(),
                        "status": "failed",
                        "error_reason": result['error'],
                        "campaign_id": campaign_id
                    }
                    
                    await db.db.messages.insert_one(message_data)
                    failed.append({
                        **contact,
                        "error": result['error']
                    })
                
                # Update progress
                if progress_callback:
                    progress_callback(index, total, len(successful), len(failed))
                
                # Delay between messages
                if index < total:
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error processing contact {index}: {e}")
                failed.append({
                    **contact,
                    "error": str(e)
                })
        
        # Update campaign status
        await self._update_campaign(campaign_id, len(successful), len(failed))
        
        return {
            "campaign_id": str(campaign_id),
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (len(successful) / total) * 100 if total > 0 else 0
        }
    
    async def load_contacts_from_csv(self, csv_file_path: str) -> List[Dict]:
        """Load contacts from CSV file"""
        contacts = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    contacts.append(row)
            
            logger.info(f"Loaded {len(contacts)} contacts from {csv_file_path}")
            return contacts
            
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            raise
    
    def validate_contacts(self, contacts: List[Dict]) -> Dict:
        """Validate contact list"""
        valid_contacts = []
        invalid_contacts = []
        
        for contact in contacts:
            phone = contact.get('phone', '').strip()
            if not phone:
                invalid_contacts.append({
                    **contact,
                    "error": "Missing phone number"
                })
                continue
            
            # Basic phone validation
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            if len(cleaned_phone) < 10:
                invalid_contacts.append({
                    **contact,
                    "error": "Invalid phone number"
                })
                continue
            
            valid_contacts.append(contact)
        
        return {
            "valid": valid_contacts,
            "invalid": invalid_contacts,
            "total_valid": len(valid_contacts),
            "total_invalid": len(invalid_contacts)
        }
    
    def _personalize_message(self, template: str, contact: Dict) -> str:
        """Personalize message with contact data"""
        try:
            return template.format(**contact)
        except KeyError as e:
            logger.warning(f"Missing placeholder {e} in template")
            return template
    
    async def _create_campaign(self, campaign_id: ObjectId, name: str, total_contacts: int):
        """Create campaign record"""
        await db.db.campaigns.insert_one({
            "_id": campaign_id,
            "name": name,
            "total_contacts": total_contacts,
            "status": "running",
            "created_at": datetime.utcnow(),
            "started_at": datetime.utcnow()
        })
    
    async def _update_campaign(self, campaign_id: ObjectId, successful: int, failed: int):
        """Update campaign completion status"""
        status = "completed" if (successful + failed) > 0 else "failed"
        
        await db.db.campaigns.update_one(
            {"_id": campaign_id},
            {
                "$set": {
                    "status": status,
                    "successful_count": successful,
                    "failed_count": failed,
                    "completed_at": datetime.utcnow()
                }
            }
        )