from pymongo import MongoClient, TEXT

# Connect to MongoDB (replace with your connection string)
connection_string = "mongodb://localhost:27017/"
client = MongoClient(connection_string)

# Access the database and collection
db = client['freemedtube']
collection = db['courses']

# Drop existing index if it exists (optional, for re-creation)
collection.drop_index('search_index')

# Create a text index on relevant fields
# Weights: Higher for video titles (more specific), lower for course titles
collection.create_index([
    ('course_title', TEXT),
    ('chapters.chapter_title', TEXT),
    ('chapters.videos.title', TEXT)
], name='search_index', default_language='english', weights={
    'course_title': 1,
    'chapters.chapter_title': 2,
    'chapters.videos.title': 5
})

print("Text search index created successfully!")
client.close()