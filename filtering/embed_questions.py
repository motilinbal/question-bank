import re
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
import chromadb
from tqdm import tqdm

# Load the embedding model
model = SentenceTransformer("BAAI/bge-large-en-v1.5")


def get_single_embedding(
    long_text: str, chunk: bool = True, normalize: bool = True
) -> np.ndarray:
    """Generate a single embedding vector for a long string."""
    if not chunk:
        return model.encode(long_text, normalize_embeddings=normalize)

    sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s", long_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return np.zeros(model.get_sentence_embedding_dimension())

    embeddings = model.encode(
        sentences, normalize_embeddings=normalize, show_progress_bar=False
    )
    avg_embedding = np.mean(embeddings, axis=0)
    if normalize:
        avg_embedding /= np.linalg.norm(avg_embedding)

    return avg_embedding


# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["test_db"]
mongo_collection = db["Questions"]
mongo_collection_size = mongo_collection.count_documents({})

# ChromaDB setup
chroma_client = chromadb.PersistentClient(path="./chromadb")
chroma_collection = chroma_client.get_or_create_collection(
    name="Questions", metadata={"hnsw:space": "cosine"}
)

# Batch size for processing (adjust based on memory)
batch_size = 100
cursor = mongo_collection.find().batch_size(batch_size)

# Process all questions
embeddings_batch = []
ids_batch = []
embedding_dim = model.get_sentence_embedding_dimension()

for question in tqdm(cursor, total=mongo_collection_size, desc="Embedding Questions"):
    result = chroma_collection.get(ids=[str(question["_id"])], include=["embeddings"])
    if (
        result["ids"]
        and result["embeddings"] is not None
        and len(result["embeddings"]) > 0
    ):
        embedding = np.array(result["embeddings"][0])
        if embedding.shape[0] == embedding_dim and np.any(embedding != 0):
            continue

    embedding_text = (
        question["title"]
        + "\n\n"
        + question["text"]
        + "\n\n"
        + "\n\n".join(question["teaching_points"])
    )
    embedding = get_single_embedding(embedding_text, chunk=True)

    embeddings_batch.append(embedding.tolist())
    ids_batch.append(str(question["_id"]))  # Ensure ID is string

    if len(embeddings_batch) == batch_size:
        # Upsert batch (updates if exists, adds if not)
        chroma_collection.upsert(embeddings=embeddings_batch, ids=ids_batch)
        embeddings_batch = []
        ids_batch = []

# Upsert any remaining in the last batch
if embeddings_batch:
    chroma_collection.upsert(embeddings=embeddings_batch, ids=ids_batch)

print("All questions embedded and stored in ChromaDB.")

chroma_client.close()
