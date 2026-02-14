# main.py – FastAPI RAG Service (replaces BullMQ worker)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from typing import Optional

from src.config.db import connect_db, MongoDB
from src.models.document import DocumentModel
from src.pipeline.rag_pipeline import process_document_rag
from src.config.env import env


# ===================== FastAPI App =====================
app = FastAPI(
    title="RAG Processing Service",
    description="Python service for RAG pipeline processing",
    version="1.0.0"
)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== Request/Response Models =====================
class ProcessRequest(BaseModel):
    """
    Request model matching Node.js RagJobData
    """
    documentId: str
    userId: str
    chatId: str
    storagePath: str
    fileName: str


class ProcessResponse(BaseModel):
    """
    Response model matching TypeScript interface
    """
    success: bool
    pageCount: int
    totalChunks: int
    error: Optional[str] = None


# ===================== Global State =====================
document_model: DocumentModel | None = None


# ===================== Startup/Shutdown Events =====================
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    global document_model
    
    db = await connect_db()
    document_model = DocumentModel(db)
    print("✅ MongoDB connected")
    print(f"🚀 RAG Service started on port {env.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown"""
    await MongoDB.close()
    print("✅ MongoDB closed")


# ===================== Health Check Endpoint =====================
@app.get("/")
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    mem = process.memory_info()
    
    return {
        "status": "ok",
        "service": "rag-service",
        "uptime": process.create_time(),
        "memory": {
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
        }
    }


# ===================== Main Processing Endpoint =====================
@app.post("/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """
    Main RAG processing endpoint
    
    This endpoint:
    1. Receives job data from Node.js worker
    2. Updates document status to 'processing'
    3. Runs the RAG pipeline
    4. Updates document status to 'processed' or 'failed'
    5. Returns result
    
    Args:
        request: ProcessRequest with document details
        
    Returns:
        ProcessResponse with success status and metrics
        
    Raises:
        HTTPException: If processing fails
    """
    document_id = request.documentId
    user_id = request.userId
    chat_id = request.chatId
    storage_path = request.storagePath
    file_name = request.fileName
    
    print(f"📥 Processing document: {file_name}")
    
    try:
        # Mark as processing
        await document_model.find_by_id_and_update(
            document_id, 
            {"status": "processing"}
        )
        
        # Run RAG pipeline
        result = await process_document_rag(
            document_id=document_id,
            user_id=user_id,
            chat_id=chat_id,
            storage_path=storage_path,
        )
        
        # Check if pipeline succeeded
        if not result.success:
            raise Exception(result.error or "RAG processing failed")
        
        # Update document status
        await document_model.find_by_id_and_update(
            document_id,
            {
                "status": "processed",
                "pageCount": result.page_count,
            }
        )
        
        print(f"✅ Document processed | Pages: {result.page_count}")
        
        return ProcessResponse(
            success=True,
            pageCount=result.page_count,
            totalChunks=result.total_chunks,
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Processing failed: {error_msg}")
        
        # Update document status to failed
        await document_model.find_by_id_and_update(
            document_id, 
            {"status": "failed"}
        )
        
        # Return error response (don't raise HTTPException to allow retries)
        return ProcessResponse(
            success=False,
            pageCount=0,
            totalChunks=0,
            error=error_msg,
        )


# ===================== Run Server =====================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=env.PORT,
        reload=False,  # Disable in production
        log_level="info"
    )