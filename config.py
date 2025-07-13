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
IMAGES_COLLECTION = "Images"
AUDIO_COLLECTION = "Audio"
VIDEOS_COLLECTION = "Videos"
SOURCES_COLLECTION = "sources" # This might not be needed

# --- Asset Paths ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
VIDEOS_DIR = os.path.join(STATIC_DIR, "videos")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")

# IMAGES_DIR = '/home/motilin/Documents/Medical/Docs/Mongo_Banks/Media_test/Images'
# AUDIO_DIR = '/home/motilin/Documents/Medical/Docs/Mongo_Banks/Media_test/Audio'
# VIDEO_DIR = '/home/motilin/Documents/Medical/Docs/Mongo_Banks/Media_test/Videos'

