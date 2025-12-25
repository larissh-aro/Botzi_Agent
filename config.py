# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "https://easynote-backend-1.onrender.com")
TASK_PATH = os.getenv("TASK_PATH", "/notes")  # change to /tasks if needed
