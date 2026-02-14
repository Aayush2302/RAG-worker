# models/document.py
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo.database import Database


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class Document(BaseModel):
    """
    Document model matching TypeScript IDocument interface
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    owner_id: PyObjectId = Field(alias="ownerId")
    chat_id: PyObjectId = Field(alias="chatId")
    file_name: str = Field(alias="fileName")
    storage_path: str = Field(alias="storagePath")
    size: int
    status: Literal["uploaded", "processing", "processed", "failed"] = "uploaded"
    page_count: Optional[int] = Field(default=0, alias="pageCount")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, alias="updatedAt")
    
    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class DocumentModel:
    """
    Document database operations
    Matches TypeScript DocumentModel functionality
    """
    
    def __init__(self, db: Database):
        self.collection = db['documents']
        # Create indexes
        self.collection.create_index("ownerId")
        self.collection.create_index("chatId")
        self.collection.create_index("status")
    
    async def find_by_id_and_update(self, document_id: str, update_data: dict) -> Optional[Document]:
        """
        Update document by ID
        Matches: DocumentModel.findByIdAndUpdate()
        """
        try:
            result = self.collection.find_one_and_update(
                {"_id": ObjectId(document_id)},
                {"$set": {**update_data, "updatedAt": datetime.utcnow()}},
                return_document=True
            )
            return Document(**result) if result else None
        except Exception as e:
            print(f"❌ Error updating document: {e}")
            return None
    
    def find_by_id(self, document_id: str) -> Optional[Document]:
        """Find document by ID"""
        try:
            result = self.collection.find_one({"_id": ObjectId(document_id)})
            return Document(**result) if result else None
        except Exception as e:
            print(f"❌ Error finding document: {e}")
            return None
