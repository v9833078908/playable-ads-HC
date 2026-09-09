"""Simple test for Imagen API - bypasses services/__init__.py"""

import os
import sys
import importlib.util
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Direct import of imagen_client module to bypass services/__init__.py
spec = importlib.util.spec_from_file_location(
    "imagen_client",
    Path(__file__).parent / "services" / "imagen_client.py"
)
imagen_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imagen_module)

ImagenClient = imagen_module.ImagenClient

# Simple test
def main():
    print("=" * 60)
    print("🧪 SIMPLE IMAGEN API TEST")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return

    print(f"✅ API Key found: {api_key[:20]}...")

    # Initialize client
    try:
        client = ImagenClient()
        print(f"✅ Client initialized with model: {client.model}")
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return

    # Generate simple image
    prompt = (
        "A simple blue circle on white background, "
        "centered, clean, minimal"
    )

    print(f"\n📝 Prompt: {prompt}")
    print("⏳ Generating image...")

    try:
        image = client.generate_image(
            prompt=prompt,
            aspect_ratio="1:1",
            image_size="1K"
        )

        output_path = "test_imagen_simple_output.png"
        image.save(output_path)

        print(f"✅ SUCCESS!")
        print(f"   Size: {image.size}")
        print(f"   Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
