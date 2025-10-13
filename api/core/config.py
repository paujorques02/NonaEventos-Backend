import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Calendar OAuth settings
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

# Base URL determination
if os.getenv("VERCEL"):
    # Production environment on Vercel
    BASE_URL = f"https://{os.getenv('VERCEL_URL')}"
else:
    # Local development environment
    BASE_URL = "http://localhost:8000"

# CORS settings
ORIGINS = [
    # URLs para desarrollo local
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    # URL de producción del frontend en Vercel
    "https://nona-eventos-front-end.vercel.app",
]