from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: MongoClient = None
    db = None
    
    @classmethod
    def connect_to_mongo(cls):
        try:
            cls.client = MongoClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DATABASE_NAME]
            
            # Test connection
            cls.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Create indexes
            cls.db.users.create_index("username", unique=True)
            cls.db.users.create_index("email", unique=True)
            cls.db.users.create_index("hwid", unique=True, sparse=True)
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    def close_mongo_connection(cls):
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_db(cls):
        return cls.db