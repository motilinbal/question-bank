# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "documedica_refactored")

# --- Collection Names ---
QUESTIONS_COLLECTION = "Questions"
MEDIA_COLLECTION = "Images"  # We'll need to check your data structure
SOURCES_COLLECTION = "sources"  # This might need to be created

# --- Asset Paths ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
VIDEOS_DIR = os.path.join(ASSETS_DIR, "videos")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
