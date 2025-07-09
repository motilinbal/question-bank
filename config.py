# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "documedica_refactored")

# --- Collection Names ---
QUESTIONS_COLLECTION = "questions"
MEDIA_COLLECTION = "media"
SOURCES_COLLECTION = "sources"

# --- Asset Paths ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
VIDEOS_DIR = os.path.join(ASSETS_DIR, "videos")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
