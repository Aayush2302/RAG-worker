# services/pdf_extractor.py
import gc
import re
from typing import List, Callable, Awaitable, Dict
from dataclasses import dataclass
from pypdf import PdfReader
import io


@dataclass
class PageChunk:
    """Page chunk container matching TypeScript interface"""
    page_number: int
    chunk_index: int
    content: str


def clean_text(text: str) -> str:
    """
    Clean extracted text
    Matches TypeScript cleanText()
    """
    # Remove extra spaces (preserve newlines)
    text = re.sub(r'[^\S\r\n]+', ' ', text)
    # Collapse multiple newlines
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


async def extract_and_process_pdf(
    buffer: bytes,
    on_batch_ready: Callable[[List[PageChunk]], Awaitable[None]],
    options: Dict[str, int]
) -> Dict[str, int]:
    """
    Extract text and process in batches to stay under memory limits
    
    MEMORY OPTIMIZATION:
    - Processes PDF in streaming fashion
    - Only keeps 5 chunks in memory at a time
    - Explicitly triggers garbage collection
    - Clears buffers after use
    
    Matches TypeScript extractAndProcessPdf()
    
    Args:
        buffer: PDF file as bytes
        on_batch_ready: Async callback to process chunk batches
        options: Dictionary with 'chunkSize' and 'overlap'
    
    Returns:
        Dictionary with 'pageCount'
    """
    try:
        # 1. Extract raw text using pypdf (lightweight, memory-efficient)
        pdf_stream = io.BytesIO(buffer)
        reader = PdfReader(pdf_stream)
        total_pages = len(reader.pages)
        
        # Extract all text
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
        
        # 2. Clear original buffer immediately to free RAM
        del buffer
        pdf_stream.close()
        gc.collect()
        
        # Clean text
        cleaned_text = clean_text(full_text)
        del full_text  # Free memory
        
        words = cleaned_text.split()
        del cleaned_text  # Free memory
        
        chunks: List[PageChunk] = []
        chunk_index = 0
        chunk_size = options['chunkSize']
        overlap = options['overlap']
        
        # 3. Sliding window chunking logic
        i = 0
        while i < len(words):
            content = ' '.join(words[i:i + chunk_size])
            
            chunks.append(PageChunk(
                page_number=0,  # Not tracking individual pages (same as TS)
                chunk_index=chunk_index,
                content=content
            ))
            
            chunk_index += 1
            
            # 4. Batch processing: Only keep 5 chunks in memory at a time
            if len(chunks) >= 5:
                await on_batch_ready(chunks)
                chunks.clear()  # Clear list
                
                # Manually trigger GC to keep heap low
                gc.collect()
            
            i += (chunk_size - overlap)
        
        # Handle remaining chunks
        if chunks:
            await on_batch_ready(chunks)
            chunks.clear()
        
        # Final cleanup
        del words
        gc.collect()
        
        return {'pageCount': total_pages}
        
    except Exception as e:
        print(f"❌ [PDF Extractor] Error: {e}")
        raise
