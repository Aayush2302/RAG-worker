# services/vector_store.py
from typing import List
from dataclasses import dataclass
from src.config.supabase import supabase_admin


@dataclass
class VectorChunk:
    """Vector chunk container matching TypeScript interface"""
    document_id: str
    user_id: str
    chat_id: str
    page_number: int
    chunk_index: int
    content: str
    embedding: List[float]


async def store_batch_vectors(chunks: List[VectorChunk]) -> None:
    """
    Batch insert vectors into Supabase
    
    OPTIMIZED for memory and performance
    Matches TypeScript storeBatchVectors()
    
    Args:
        chunks: List of VectorChunk objects to store
    """
    if not chunks:
        return
    
    try:
        # Convert to database row format
        rows = [
            {
                'document_id': chunk.document_id,
                'user_id': chunk.user_id,
                'chat_id': chunk.chat_id,
                'page_number': chunk.page_number,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'embedding': chunk.embedding,
            }
            for chunk in chunks
        ]
        
        # Batch insert
        response = supabase_admin.table('document_chunks').insert(rows).execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ [VectorStore] Batch insert failed: {response.error}")
            raise Exception("Failed to store vectors")
            
    except Exception as error:
        print(f"❌ [VectorStore] Batch insert failed: {error}")
        raise Exception("Failed to store vectors")


async def delete_document_vectors(document_id: str) -> None:
    """
    Delete all vectors for a document
    Matches TypeScript deleteDocumentVectors()
    
    Args:
        document_id: Document ID to delete vectors for
    """
    try:
        response = supabase_admin.table('document_chunks')\
            .delete()\
            .eq('document_id', document_id)\
            .execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ [VectorStore] Delete failed: {response.error}")
            raise Exception("Failed to delete vectors")
            
    except Exception as error:
        print(f"❌ [VectorStore] Delete failed: {error}")
        raise Exception("Failed to delete vectors")
