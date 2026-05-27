from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FAST_MODEL = os.getenv("FAST_MODEL", "llama-3.3-70b-versatile")
DEEP_MODEL = os.getenv("DEEP_MODEL", "llama-3.3-70b-versatile")
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
