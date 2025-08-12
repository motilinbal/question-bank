import re
import numpy as np
from sentence_transformers import SentenceTransformer, util
import weaviate
from weaviate.classes.config import Configure, Property, DataType

# Load the embedding model (downloads automatically if not cached)
model = SentenceTransformer('BAAI/bge-large-en-v1.5')

def get_single_embedding(long_text: str, chunk: bool = True, normalize: bool = True) -> np.ndarray:
    """
    Generate a single embedding vector for a long string.
    
    Args:
        long_text (str): The input text.
        chunk (bool): Split into sentences and average embeddings for long texts.
        normalize (bool): Normalize to unit length.
    
    Returns:
        np.ndarray: The 1024-dim embedding vector.
    """
    if not chunk:
        embedding = model.encode(long_text, normalize_embeddings=normalize)
        return embedding
    
    # Chunking: Split into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', long_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return np.zeros(model.get_sentence_embedding_dimension())
    
    # Encode chunks in batch
    embeddings = model.encode(sentences, normalize_embeddings=normalize, show_progress_bar=False)
    
    # Average and re-normalize
    avg_embedding = np.mean(embeddings, axis=0)
    if normalize:
        avg_embedding /= np.linalg.norm(avg_embedding)
    
    return avg_embedding

# Set up local embedded Weaviate
client = weaviate.connect_to_embedded(
    # version="1.26.5",  # Optional: Specify a version; defaults to latest
    persistence_data_path="./weaviate_data",  # Local persistence directory
    environment_variables={"LOG_LEVEL": "WARNING"}  # Reduce logs
)

# Collection name and config (vector dim matches BGE-large-en-v1.5)
collection_name = "Questions"
embedding_dim = model.get_sentence_embedding_dimension()  # 1024

# Create collection if it doesn't exist (with no built-in vectorizer)
collections = client.collections.list_all()
if collection_name not in collections:
    client.collections.create(
        name=collection_name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT)  # Store original text
        ],
        vector_index_config=Configure.VectorIndex.hnsw(  # Efficient index for search
            ef_construction=128,
            m=16
        )
    )

# Get the collection
collection = client.collections.get(collection_name)

# Example usage: Generate and store embedding
long_string = """
This is an example of a long string that might exceed the 512-token limit. 
It contains multiple sentences. For instance, here's one. And another! 
What about questions? Yes, those too. The goal is to create a single embedding 
vector representing the entire text without losing key information.
"""
embedding = get_single_embedding(long_string, chunk=True)

# Store in Weaviate (as list for compatibility)
object_uuid = collection.data.insert({
    "text": long_string,
    "vector": embedding.tolist()
})
print(f"Stored object with UUID: {object_uuid}")

# Demonstrate search accessibility (near-vector query)
query_embedding = get_single_embedding("A long text about sentences and questions.", chunk=True)
response = collection.query.near_vector(
    near_vector=query_embedding.tolist(),
    limit=1,
    return_properties=["text"]
)
if response.objects:
    print("Top match text:", response.objects[0].properties["text"])
else:
    print("No matches found.")

# Cleanup: Close client (embedded instance stops)
client.close()