# pipeline/rag_pipeline.py
import gc
from typing import Dict, List
from dataclasses import dataclass

from src.config.supabase import supabase_admin
from src.services.pdf_extractor import extract_and_process_pdf, PageChunk
from src.services.embedder import generate_batch_embeddings
from src.services.vector_store import store_batch_vectors, VectorChunk


@dataclass
class PipelineResult:
    """Pipeline result matching TypeScript interface"""
    success: bool
    page_count: int
    total_chunks: int
    error: str = None


async def process_document_rag(
    document_id: str,
    user_id: str,
    chat_id: str,
    storage_path: str
) -> PipelineResult:
    """
    Main RAG Pipeline optimized for low-memory environments
    
    MEMORY OPTIMIZATION STRATEGY:
    1. Download PDF and convert to buffer
    2. Process in streaming batches (5 chunks at a time)
    3. Generate embeddings for each batch
    4. Store vectors immediately
    5. Clear batch data and trigger GC
    6. Repeat until complete
    
    This ensures we never hold the entire document + embeddings in memory
    
    Matches TypeScript processDocumentRAG()
    
    Args:
        document_id: MongoDB document ID
        user_id: Owner user ID
        chat_id: Associated chat ID
        storage_path: Supabase storage path
    
    Returns:
        PipelineResult with success status and metrics
    """
    print(f"🚀 [RAG Pipeline] Starting: {document_id}")
    
    total_chunks_processed = 0
    
    try:
        # 1. Download PDF from Supabase Storage
        response = supabase_admin.storage.from_('pdf-uploads').download(storage_path)
        
        if not response:
            raise Exception(f"Download failed: No data returned")
        
        # 2. Convert to bytes buffer
        buffer = response
        print(f"📦 PDF Downloaded. Size: {len(buffer) / 1024 / 1024:.2f} MB")
        
        # 3. Define batch processing callback
        async def handle_batch(chunks: List[PageChunk]) -> None:
            """Process a batch of chunks: Embed -> Store -> Clear"""
            nonlocal total_chunks_processed
            
            await handle_batch_processing(
                chunks, document_id, user_id, chat_id
            )
            total_chunks_processed += len(chunks)
        
        # 4. Extract and Process via streaming callback
        result = await extract_and_process_pdf(
            buffer,
            handle_batch,
            {'chunkSize': 250, 'overlap': 30}
        )
        
        # 5. Final Cleanup
        del buffer
        gc.collect()
        
        print(f"✅ [RAG] Complete: {result['pageCount']} pages, {total_chunks_processed} chunks.")
        
        return PipelineResult(
            success=True,
            page_count=result['pageCount'],
            total_chunks=total_chunks_processed
        )
        
    except Exception as error:
        print(f"❌ [RAG Pipeline] Fatal Error: {error}")
        return PipelineResult(
            success=False,
            page_count=0,
            total_chunks=0,
            error=str(error)
        )
    finally:
        # Final GC trigger
        gc.collect()


async def handle_batch_processing(
    chunks: List[PageChunk],
    document_id: str,
    user_id: str,
    chat_id: str
) -> None:
    """
    Helper to process a small batch of chunks: Embed -> Store -> Clear
    
    MEMORY OPTIMIZATION:
    - Only processes 5 chunks at a time
    - Clears intermediate data structures
    - Triggers garbage collection
    
    Matches TypeScript handleBatchProcessing()
    
    Args:
        chunks: List of PageChunk objects (max 5)
        document_id: Document ID
        user_id: User ID
        chat_id: Chat ID
    """
    try:
        # Extract text content
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings via Jina AI
        embeddings = generate_batch_embeddings(texts)
        
        # Map to VectorStore format
        vector_chunks: List[VectorChunk] = [
            VectorChunk(
                document_id=document_id,
                user_id=user_id,
                chat_id=chat_id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embeddings[idx].embedding
            )
            for idx, chunk in enumerate(chunks)
        ]
        
        # Batch insert into Supabase/Postgres
        await store_batch_vectors(vector_chunks)
        
        print(f"  📊 Stored batch: {len(chunks)} chunks")
        
        # CRITICAL: Explicitly clear references for Garbage Collection
        texts.clear()
        vector_chunks.clear()
        embeddings.clear()
        
        # Trigger GC
        gc.collect()
        
    except Exception as error:
        print(f"  ❌ [Batch Error]: {error}")
        raise  # Re-throw to stop pipeline on DB/API failure
