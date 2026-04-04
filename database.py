from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import datetime

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db.db = db.client[settings.DATABASE_NAME]
        print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
        
        # Create indexes
        await db.db.users.create_index("username", unique=True)
        await db.db.users.create_index("email", unique=True)
        
        # Create gameplay collection if it doesn't exist
        collections = await db.db.list_collection_names()
        if "gameplay" not in collections:
            await db.db.create_collection("gameplay")
            print("✅ Created gameplay collection")
        
        print("✅ Database indexes created")
        return True
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("✅ MongoDB connection closed")

def get_current_time():
    """Get current timestamp"""
    return datetime.datetime.utcnow()