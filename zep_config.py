# zep_config.py
from zep_python.client import Zep
from zep_python import Message
from dotenv import load_dotenv
import os

load_dotenv()

zep_api = os.getenv("ZEP_API")

client = Zep(base_url="http://localhost:8000", api_key=zep_api)
