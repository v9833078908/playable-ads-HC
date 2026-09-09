#!/usr/bin/env python3
"""Quick test to check FAL LLM API"""

import os
import fal_client

# Load FAL_KEY from .env
from pathlib import Path
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

print("Testing FAL LLM API...")
print(f"FAL_KEY set: {bool(os.getenv('FAL_KEY'))}")

# Try different model names that FAL might support
models_to_try = [
    "fal-ai/gemini-25-flash-image",  # Primary model for asset generation
    "fal-ai/any-llm",  # FAL's universal LLM endpoint
]

test_prompt = """Return a simple JSON array with one item:
[{"name": "test", "value": 123}]"""

for model in models_to_try:
    print(f"\n--- Testing model: {model} ---")
    try:
        result = fal_client.run(
            model,
            arguments={
                "prompt": test_prompt,
                "max_tokens": 100
            }
        )
        print(f"✅ Success! Result type: {type(result)}")
        print(f"Result: {result}")

        # Try to extract text
        if isinstance(result, dict):
            text = result.get("text") or result.get("output") or result.get("content") or str(result)
        else:
            text = str(result)

        print(f"Extracted text: {text[:200]}")
        break  # Success, stop trying

    except Exception as e:
        print(f"❌ Failed: {e}")

print("\nDone!")
