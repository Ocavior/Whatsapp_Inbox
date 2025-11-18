# test_connection.py
from app.database.mongodb import get_database

def test_connection():
    db = get_database()
    if db:
        print("✅ Connection successful!")
        print(f"Database name: {db.name}")
        
        # List collections to verify
        collections = db.list_collection_names()
        print(f"Collections: {collections}")
    else:
        print("❌ Connection failed!")

if __name__ == "__main__":
    test_connection()
