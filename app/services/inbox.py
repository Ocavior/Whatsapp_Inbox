from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.database.mongodb import db
from app.models.message import Message, MessageStatus, MessageDirection
from app.utils.logger import logger


class InboxService:
    """Service for managing messages and conversations"""
    
    async def save_message(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Save message to database"""
        try:
            message = Message(**message_data)
            
            result = await db.db.messages.insert_one(message.dict(by_alias=True))
            message_id = str(result.inserted_id)
            
            # Update conversation
            await self._update_conversation(message)
            
            logger.info(f"Message saved for user {message.user_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None
    
    async def update_message_status(self, message_id: str, status: MessageStatus, 
                                  error_reason: Optional[str] = None) -> bool:
        """Update message status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if error_reason:
                update_data["error_reason"] = error_reason
            
            result = await db.db.messages.update_one(
                {"message_id": message_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # Get the message to update conversation
                message = await db.db.messages.find_one({"message_id": message_id})
                if message:
                    await self._update_conversation(Message(**message))
                
                logger.info(f"Message {message_id} status updated to {status}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
            return False
    
    async def get_user_messages(self, user_id: str, limit: int = 100, 
                              skip: int = 0) -> List[Dict]:
        """Get messages for a specific user"""
        try:
            cursor = db.db.messages.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).skip(skip).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages for {user_id}: {e}")
            return []
    
    async def get_conversations(self, limit: int = 50, skip: int = 0, 
                              archived: bool = False) -> List[Dict]:
        """Get all conversations"""
        try:
            query = {"is_archived": archived}
            cursor = db.db.conversations.find(query).sort(
                "last_message_timestamp", -1
            ).skip(skip).limit(limit)
            
            conversations = await cursor.to_list(length=limit)
            return conversations
            
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
            return []
    
    async def search_messages(self, query: str, user_id: Optional[str] = None,
                            limit: int = 50) -> List[Dict]:
        """Search messages by content"""
        try:
            search_filter = {"body": {"$regex": query, "$options": "i"}}
            if user_id:
                search_filter["user_id"] = user_id
            
            cursor = db.db.messages.find(search_filter).sort(
                "timestamp", -1
            ).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            return messages
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []
    
    async def _update_conversation(self, message: Message):
        """Update conversation when new message arrives"""
        try:
            conversation_data = {
                "user_id": message.user_id,
                "last_message": message.body[:500],  # Truncate long messages
                "last_message_timestamp": message.timestamp,
                "last_message_direction": message.direction,
                "updated_at": datetime.utcnow()
            }
            
            # Increment unread count for inbound messages
            if message.direction == MessageDirection.INBOUND:
                conversation_data["$inc"] = {
                    "unread_count": 1,
                    "total_messages": 1
                }
            else:
                conversation_data["$inc"] = {"total_messages": 1}
            
            await db.db.conversations.update_one(
                {"user_id": message.user_id},
                {
                    "$set": conversation_data,
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                        "is_archived": False,
                        "labels": []
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")