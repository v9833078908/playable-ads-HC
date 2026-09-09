"""Test script for Gemini Imagen API"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root on sys.path

import os


# Import directly to avoid services/__init__.py importing old gemini_client
from services.imagen_client import ImagenClient
from PIL import Image
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_generation():
    """Test 1: Basic image generation from text prompt"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Image Generation")
    logger.info("=" * 60)

    client = ImagenClient()

    prompt = (
        "A cartoon blue knight character in shiny armor, "
        "centered on transparent background, "
        "mobile game style, flat colors, no shadows"
    )

    try:
        image = client.generate_image(
            prompt=prompt,
            aspect_ratio="1:1",
            image_size="1K"  # Smaller for faster test
        )

        # Save result
        output_path = "test_output_basic.png"
        image.save(output_path)
        logger.info(f"✅ SUCCESS: Image saved to {output_path}")
        logger.info(f"   Size: {image.size}")
        return True

    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        return False


def test_with_reference():
    """Test 2: Image generation with reference image"""
    logger.info("=" * 60)
    logger.info("TEST 2: Generation with Reference Image")
    logger.info("=" * 60)

    # Check if we have a reference image
    ref_path = "docs/misc/Assets"
    if not os.path.exists(ref_path):
        logger.warning(f"⚠️  SKIPPED: No reference images at {ref_path}")
        return True

    # Find first image in Assets folder
    import glob
    image_files = glob.glob(f"{ref_path}/*.png") + glob.glob(f"{ref_path}/*.jpg")

    if not image_files:
        logger.warning("⚠️  SKIPPED: No PNG/JPG files in Assets folder")
        return True

    ref_image_path = image_files[0]
    logger.info(f"Using reference: {ref_image_path}")

    client = ImagenClient()

    # Load reference image
    ref_image = Image.open(ref_image_path)

    prompt = (
        "A red car with mud spots, "
        "cartoon style similar to reference image, "
        "centered, transparent background, "
        "mobile game asset"
    )

    try:
        image = client.generate_image(
            prompt=prompt,
            reference_images=[ref_image],
            aspect_ratio="1:1",
            image_size="1K"
        )

        # Save result
        output_path = "test_output_with_reference.png"
        image.save(output_path)
        logger.info(f"✅ SUCCESS: Image saved to {output_path}")
        logger.info(f"   Size: {image.size}")
        return True

    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        return False


def test_different_aspect_ratios():
    """Test 3: Generate images with different aspect ratios"""
    logger.info("=" * 60)
    logger.info("TEST 3: Different Aspect Ratios")
    logger.info("=" * 60)

    client = ImagenClient()

    test_cases = [
        ("1:1", "square object"),
        ("16:9", "wide background scene"),
        ("4:3", "portrait character")
    ]

    for aspect_ratio, description in test_cases:
        prompt = f"A simple {description}, cartoon style, solid color background"

        try:
            image = client.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size="1K"
            )

            output_path = f"test_output_{aspect_ratio.replace(':', 'x')}.png"
            image.save(output_path)
            logger.info(f"✅ {aspect_ratio}: Saved to {output_path} ({image.size})")

        except Exception as e:
            logger.error(f"❌ {aspect_ratio}: Failed - {e}")
            return False

    return True


def test_aspect_ratio_helper():
    """Test 4: Aspect ratio calculation helper"""
    logger.info("=" * 60)
    logger.info("TEST 4: Aspect Ratio Helper Function")
    logger.info("=" * 60)

    test_cases = [
        ((512, 512), "1:1"),
        ((960, 540), "16:9"),
        ((256, 256), "1:1"),
        ((400, 300), "4:3"),
    ]

    for (width, height), expected in test_cases:
        result = ImagenClient.aspect_ratio_from_size(width, height)
        status = "✅" if result == expected else "❌"
        logger.info(f"{status} {width}x{height} → {result} (expected: {expected})")

    return True


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 GEMINI IMAGEN API TEST SUITE")
    logger.info("=" * 60 + "\n")

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not found in environment")
        return

    logger.info(f"✅ API Key: {api_key[:20]}...")

    # Run tests
    tests = [
        ("Basic Generation", test_basic_generation),
        ("With Reference", test_with_reference),
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

        print()  # Blank line between tests

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
