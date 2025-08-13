import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
import torch  # For device check
import re, pymongo

# Load the embedding model (same as your script)
model = SentenceTransformer("BAAI/bge-large-en-v1.5")

# GPU setup (optional, for faster embedding)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)
if device == 'cuda':
    model.half()  # FP16 on GPU for speed

def get_single_embedding(
    long_text: str, chunk: bool = True, normalize: bool = True
) -> np.ndarray:
    """Generate a single embedding vector for a long string (from your script)."""
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

# MongoDB setup
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["test_db"]
mongo_collection = db["Questions"]

# Set up Chroma client (persistent, matching your script)
chroma_client = chromadb.HttpClient(host='localhost', port=8000)
chroma_collection = chroma_client.get_collection(name="Questions")

# Example query string (e.g., a search phrase)
query_string = "Hypovolemic shock and baroreceptor activity."

# Embed the query
query_embedding = get_single_embedding(query_string, chunk=True)

# Perform vector search (top 5 similar results)
k = 5  # Number of results
response = chroma_collection.query(
    query_embeddings=[query_embedding.tolist()],
    n_results=k
)

# Extract and print results (IDs for Mongo lookup, with distances)
if response['ids'] and response['ids'][0]:
    for idx, q_id in enumerate(response['ids'][0]):
        distance = response['distances'][0][idx]  # Lower is more similar (cosine)
        print(f"- ID: {q_id} (distance: {distance:.4f})")
        question = mongo_collection.find_one({"_id": q_id})
        print(question['title'])
        print(question['text'])
        print('\n\n'.join(question['teaching_points']))
        print('\n' + '='*50 + '\n')
else:
    print("No matches found.")
