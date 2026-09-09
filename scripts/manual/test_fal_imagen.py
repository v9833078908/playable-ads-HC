"""Test FAL.AI Gemini Image Generation"""

from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Load environment
load_dotenv()

# Import FAL client directly (bypass services/__init__.py)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "fal_imagen_client",
    Path(__file__).parent / "services" / "fal_imagen_client.py"
)
fal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fal_module)
FALImagenClient = fal_module.FALImagenClient

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_generation():
    """Test 1: Basic text-to-image generation"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Image Generation via FAL.AI")
    logger.info("=" * 60)

    # Check API key
    api_key = os.getenv("FAL_KEY")
    if not api_key:
        logger.error("❌ FAL_KEY not found in environment")
        logger.error("   Please add FAL_KEY to .env file")
        logger.error("   Get your key from: https://fal.ai/dashboard/keys")
        return False

    logger.info(f"✅ FAL_KEY found: {api_key[:20]}...")

    try:
        # Initialize client
        client = FALImagenClient()
        logger.info(f"✅ Client initialized")

        # Generate image
        prompt = (
            "A cartoon blue knight character in shiny armor, "
            "centered on white background, "
            "mobile game style, flat colors, simple design"
        )

        logger.info(f"📝 Prompt: {prompt}")
        logger.info("⏳ Generating image (this may take 10-30 seconds)...")

        image = client.generate_image(
            prompt=prompt,
            aspect_ratio="1:1",
            output_format="png"
        )

        # Save result
        output_path = "test_fal_output_basic.png"
        image.save(output_path)

        logger.info(f"✅ SUCCESS!")
        logger.info(f"   Image size: {image.size}")
        logger.info(f"   Saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_aspect_ratios():
    """Test 2: Generate with different aspect ratios"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Different Aspect Ratios")
    logger.info("=" * 60)

    api_key = os.getenv("FAL_KEY")
    if not api_key:
        logger.warning("⚠️  SKIPPED: FAL_KEY not found")
        return True

    try:
        client = FALImagenClient()

        test_cases = [
            ("1:1", "a simple red circle"),
            ("16:9", "a wide landscape scene with mountains"),
            ("4:3", "a portrait of a cute dog")
        ]

        for aspect_ratio, description in test_cases:
            logger.info(f"\n→ Testing {aspect_ratio}: {description}")

            image = client.generate_image(
                prompt=description,
                aspect_ratio=aspect_ratio
            )

            output_path = f"test_fal_output_{aspect_ratio.replace(':', 'x')}.png"
            image.save(output_path)

            logger.info(f"   ✅ Saved to {output_path} ({image.size})")

        return True

    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        return False


def test_aspect_ratio_helper():
    """Test 3: Aspect ratio calculation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Aspect Ratio Helper")
    logger.info("=" * 60)

    test_cases = [
        ((512, 512), "1:1"),
        ((960, 540), "16:9"),
        ((256, 256), "1:1"),
        ((400, 300), "4:3"),
    ]

    for (width, height), expected in test_cases:
        result = FALImagenClient.aspect_ratio_from_size(width, height)
        status = "✅" if result == expected else "❌"
        logger.info(f"{status} {width}x{height} → {result} (expected: {expected})")

    return True


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 FAL.AI GEMINI IMAGE GENERATION TEST SUITE")
    logger.info("=" * 60 + "\n")

    # Run tests
    tests = [
        ("Basic Generation", test_basic_generation),
        ("Aspect Ratios", test_different_aspect_ratios),
        ("Helper Functions", test_aspect_ratio_helper),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}", exc_info=True)
            results.append((name, False))

        print()  # Blank line

    # Summary
    logger.info("=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
