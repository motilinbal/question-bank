# vector_search_service.py
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
import torch  # For device check
import re
import pymongo
import config
import streamlit as st

# Global variables for singleton pattern
_model = None
_chroma_client = None
_chroma_collection = None
_mongo_client = None
_mongo_collection = None

def _get_model():
    """Lazy loading of the SentenceTransformer model (singleton pattern)."""
    global _model
    if _model is None:
        with st.spinner("Loading AI model for vector search (this may take a moment)..."):
            _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
            
            # GPU setup (optional, for faster embedding)
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            _model = _model.to(device)
            if device == 'cuda':
                _model.half()  # FP16 on GPU for speed
    
    return _model

def _get_chroma_collection():
    """Get the ChromaDB collection (singleton pattern)."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        # Set up Chroma client (persistent, matching your script)
        _chroma_client = chromadb.HttpClient(host='localhost', port=8000)
        _chroma_collection = _chroma_client.get_collection(name="Questions")
    
    return _chroma_collection

def _get_mongo_collection():
    """Get the MongoDB collection (singleton pattern)."""
    global _mongo_client, _mongo_collection
    if _mongo_collection is None:
        # MongoDB setup
        _mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = _mongo_client["test_db"]
        _mongo_collection = db["Questions"]
    
    return _mongo_collection

def get_single_embedding(
    long_text: str, chunk: bool = True, normalize: bool = True
) -> np.ndarray:
    """Generate a single embedding vector for a long string (from your script)."""
    model = _get_model()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    if not chunk:
        return model.encode(long_text, normalize_embeddings=normalize, device=device)

    sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s", long_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return np.zeros(model.get_sentence_embedding_dimension())

    embeddings = model.encode(
        sentences, normalize_embeddings=normalize, show_progress_bar=False, device=device
    )
    avg_embedding = np.mean(embeddings, axis=0)
    if normalize:
        avg_embedding /= np.linalg.norm(avg_embedding)

    return avg_embedding

def perform_vector_search(query_string: str) -> list[str]:
    """
    Perform vector search and return a list of question IDs.
    
    Args:
        query_string (str): The search query string
        
    Returns:
        list[str]: List of question IDs that match the vector search
    """
    try:
        # Get embeddings model and collections
        model = _get_model()
        chroma_collection = _get_chroma_collection()
        # mongo_collection = _get_mongo_collection()  # Not needed for just getting IDs
        
        # Embed the query
        query_embedding = get_single_embedding(query_string, chunk=True)
        
        # Perform vector search (using configurable result count)
        k = config.VECTOR_SEARCH_RESULTS_COUNT
        response = chroma_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k
        )
        
        # Extract and return question IDs
        if response['ids'] and response['ids'][0]:
            return response['ids'][0]
        else:
            return []
            
    except Exception as e:
        # Handle any errors gracefully
        st.error(f"Vector search failed: {str(e)}")
        return []