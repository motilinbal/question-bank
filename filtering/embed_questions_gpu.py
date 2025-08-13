import re
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
import chromadb
from tqdm import tqdm
import torch

# Load the embedding model
model = SentenceTransformer("BAAI/bge-large-en-v1.5")

# GPU setup (move model to GPU if available and use FP16)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)
if device == 'cuda':
    model.half()  # FP16 on GPU for speed
print(f"Using device: {device}")

def get_single_embedding(
    long_text: str, chunk: bool = True, normalize: bool = True
) -> np.ndarray:
    """Generate a single embedding vector for a long string."""
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


def process_batch(batch_of_docs, chroma_collection, model, device, embedding_dim):
    """Process a batch of documents: check existence, embed new ones, and upsert."""
    if not batch_of_docs:
        return

    # Batch existence check
    batch_ids = [str(doc["_id"]) for doc in batch_of_docs]
    result = chroma_collection.get(ids=batch_ids, include=['embeddings'])
    embeddings = result['embeddings']
    if embeddings is None:
        embeddings = []
    
    existing_valid = set()  # IDs to skip
    for idx, emb_list in enumerate(embeddings):
        if emb_list is not None and len(emb_list) > 0:  # Non-None embedding
            embedding = np.array(emb_list)
            if embedding.shape == (embedding_dim,) and np.any(embedding != 0):
                existing_valid.add(result['ids'][idx])

    # Process only non-existing/invalid
    embeddings_batch = []
    ids_batch = []
    texts_batch = []  # For batch encoding
    for doc in batch_of_docs:
        q_id = str(doc["_id"])
        if q_id in existing_valid:
            continue

        embedding_text = (
            doc["title"]
            + "\n\n"
            + doc["text"]
            + "\n\n"
            + "\n\n".join(tp for tp in doc["teaching_points"])
        )
        texts_batch.append(embedding_text)
        ids_batch.append(q_id)

    if texts_batch:
        # Batch encode multiple texts at once (parallel on GPU)
        batch_embeddings = model.encode(
            texts_batch, normalize_embeddings=True, show_progress_bar=False, device=device, batch_size=32  # Sub-batch if needed for memory
        )
        # If chunking per text is still desired, you'd need to adapt; but for speed, encode full texts if <512 tokens
        # Or chunk per text, but batch chunks across texts

        # Handle averaging if chunked (but for simplicity, assuming no chunk or pre-chunk texts)
        for emb in batch_embeddings:
            embeddings_batch.append(emb.tolist())  # Or average if chunked

        chroma_collection.upsert(embeddings=embeddings_batch, ids=ids_batch)

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27018/")
db = mongo_client["test_db"]
mongo_collection = db["Questions"]
mongo_collection_size = mongo_collection.count_documents({})

# ChromaDB setup
chroma_client = chromadb.HttpClient(host='localhost', port=8000)
chroma_collection = chroma_client.get_or_create_collection(
    name="Questions", metadata={"hnsw:space": "cosine"}
)

# Batch size (larger on GPU; e.g., 512+)
batch_size = 100 if device == 'cpu' else 512
cursor = mongo_collection.find().batch_size(batch_size)

# Process in batches
embedding_dim = model.get_sentence_embedding_dimension()
batch_of_docs = []
for question in tqdm(cursor, total=mongo_collection_size, desc="Embedding Questions"):
    batch_of_docs.append(question)
    if len(batch_of_docs) == batch_size:
        process_batch(batch_of_docs, chroma_collection, model, device, embedding_dim)
        batch_of_docs = []

# Handle remaining batch
process_batch(batch_of_docs, chroma_collection, model, device, embedding_dim)

print("All questions embedded and stored in ChromaDB.")
