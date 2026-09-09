import os
from openai import AsyncOpenAI

# Initialize async client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
