# app/database/mongodb.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.MONGODB_URI = os.getenv("MONGODB_URI")
        self.DB_NAME = os.getenv("DB_NAME", "whatsapp_inbox")
    
    async def connect(self):
        """Establish database connection"""
        try:
            if not self.MONGODB_URI:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            # Connect to MongoDB
            self.client = MongoClient(self.MONGODB_URI)
            
            # Test the connection
            self.client.admin.command('ping')
            self.db = self.client[self.DB_NAME]
            
            print("✅ Successfully connected to MongoDB")
            return self.db
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return None
    
    async def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            print("🔌 MongoDB connection closed")
    
    def get_database(self):
        """Get database instance"""
        return self.db

# Create a global instance
db = MongoDB()