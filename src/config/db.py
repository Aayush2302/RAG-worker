# config/db.py
from pymongo import MongoClient
from pymongo.database import Database
from src.config.env import env
import sys


class MongoDB:
    """MongoDB connection manager"""
    _client: MongoClient = None
    _db: Database = None
    
    @classmethod
    async def connect(cls) -> Database:
        """
        Connect to MongoDB
        Returns database instance
        """
        try:
            if not env.MONGO_URI:
                raise ValueError("MONGO_URI environment variable is not defined")
            
            cls._client = MongoClient(env.MONGO_URI)
            
            # Test connection
            cls._client.admin.command('ping')
            
            # Get database name from URI or use default
            db_name = env.MONGO_URI.split('/')[-1].split('?')[0] or 'rag_database'
            cls._db = cls._client[db_name]
            
            print('✅ MongoDB connected')
            return cls._db
            
        except Exception as error:
            print(f'❌ MongoDB connection error: {error}')
            sys.exit(1)
    
    @classmethod
    def get_db(cls) -> Database:
        """Get database instance"""
        if cls._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._db
    
    @classmethod
    async def close(cls):
        """Close MongoDB connection"""
        if cls._client:
            cls._client.close()
            print('🔌 MongoDB disconnected')


# Convenience function matching TypeScript API
async def connect_db() -> Database:
    """Connect to MongoDB - matches TypeScript connectDB()"""
    return await MongoDB.connect()
