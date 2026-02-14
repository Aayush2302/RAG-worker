# services/embedder.py
import requests
from typing import List
from src.config.env import env


class EmbeddingResult:
    """Embedding result container"""
    def __init__(self, embedding: List[float]):
        self.embedding = embedding


# Jina AI v3 embeddings with 384 dimensions
JINA_API_URL = "https://api.jina.ai/v1/embeddings"


def generate_embedding(text: str) -> EmbeddingResult:
    """
    Generate single embedding using Jina AI v3
    Matches TypeScript generateEmbedding()
    """
    try:
        response = requests.post(
            JINA_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {env.JINA_API_KEY}"
            },
            json={
                "model": "jina-embeddings-v3",
                "task": "text-matching",
                "dimensions": 384,
                "input": [text]
            },
            timeout=30
        )
        
        if not response.ok:
            error_text = response.text
            raise Exception(f"Jina API error: {response.status_code} - {error_text}")
        
        data = response.json()
        return EmbeddingResult(embedding=data['data'][0]['embedding'])
        
    except Exception as error:
        print(f"❌ [Embedder] Failed: {error}")
        raise Exception("Embedding generation failed")


def generate_batch_embeddings(texts: List[str]) -> List[EmbeddingResult]:
    """
    Generate batch embeddings using Jina AI v3
    Matches TypeScript generateBatchEmbeddings()
    
    MEMORY OPTIMIZATION: Processes in batches to avoid memory spikes
    """
    if not texts:
        return []
    
    try:
        response = requests.post(
            JINA_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {env.JINA_API_KEY}"
            },
            json={
                "model": "jina-embeddings-v3",
                "task": "text-matching",
                "dimensions": 384,
                "input": texts
            },
            timeout=60
        )
        
        if not response.ok:
            error_text = response.text
            raise Exception(f"Jina API error: {response.status_code} - {error_text}")
        
        data = response.json()
        
        return [
            EmbeddingResult(embedding=item['embedding'])
            for item in data['data']
        ]
        
    except Exception as error:
        print(f"❌ [Embedder] Batch failed: {error}")
        raise Exception("Batch embedding failed")
