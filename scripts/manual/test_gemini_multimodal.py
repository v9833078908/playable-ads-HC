"""Test Gemini multimodal generation (text + image output)"""

from dotenv import load_dotenv
import os
load_dotenv()

from google import genai
from google.genai import types

print("=" * 60)
print("🧪 TEST: Gemini Multimodal Image Generation")
print("=" * 60)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found")
    exit(1)

print(f"✅ API Key: {api_key[:20]}...")

client = genai.Client(api_key=api_key)

# Try multimodal generation with image output
prompt = """Generate a simple image of a blue circle on white background.
The image should be centered, clean, and minimal."""

print(f"\n📝 Prompt: {prompt}")
print("⏳ Generating with gemini-2.0-flash-exp...")

try:
    # Try with multimodal model
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE']  # Request image output
        )
    )

    print(f"✅ Response received!")
    print(f"   Parts: {len(response.parts)}")

    # Check for images
    for i, part in enumerate(response.parts):
        print(f"\n   Part {i}: {type(part)}")
        if hasattr(part, 'inline_data') and part.inline_data:
            print(f"   → Found inline_data!")
            image = part.as_image()
            output_path = f"test_multimodal_output_{i}.png"
            image.save(output_path)
            print(f"   → Saved to {output_path}")
        elif hasattr(part, 'text'):
            print(f"   → Text: {part.text[:100]}")

except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
