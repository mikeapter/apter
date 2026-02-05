import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "local")
BOTTRADER_API_KEY = os.getenv("BOTTRADER_API_KEY")

if ENV != "local" and not BOTTRADER_API_KEY:
    raise RuntimeError("BOTTRADER_API_KEY is not set")
