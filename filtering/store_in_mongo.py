import json
from pymongo import MongoClient

# Load the JSON data
with open('filtering/freemedtube_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Connect to MongoDB (replace with your connection string)
connection_string = "mongodb://localhost:27017/"  # Or your Atlas URI
client = MongoClient(connection_string)

# Create/use database and collection
db = client['freemedtube']  # Database name
collection = db['courses']    # Collection name

# Clear existing data if needed (optional)
collection.delete_many({})

# Insert each course as a separate document
# We'll add top-level metadata to each for context
inserted_ids = []
for course in data['courses']:
    course_doc = course.copy()
    course_doc['base_url'] = data.get('base_url')
    result = collection.insert_one(course_doc)
    inserted_ids.append(result.inserted_id)

print(f"Stored {len(inserted_ids)} courses in MongoDB collection '{collection.name}'.")
client.close()