"""Gemini Imagen client for generating visual assets"""

import os
import logging
from typing import Optional
from PIL import Image as PILImage
import io

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class ImagenClient:
    """
    Client for Gemini Image Generation API.

    Uses NEW google-genai API (not deprecated google.generativeai).
    Documentation: https://ai.google.dev/gemini-api/docs/image-generation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Imagen client.

        Args:
            api_key: Gemini API key. If not provided, uses GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = genai.Client(api_key=self.api_key)

        # Models from official docs:
        # - gemini-2.5-flash-image (fast, high-volume)
        # - gemini-3-pro-image-preview (professional, advanced reasoning)
        self.model = "gemini-3-pro-image-preview"

        logger.info(f"ImagenClient initialized with model: {self.model}")

    def generate_image(
        self,
        prompt: str,
        reference_images: list[PILImage.Image] = None,
        aspect_ratio: str = "1:1",
        image_size: str = None  # Deprecated - not used in current API
    ) -> PILImage.Image:
        """
        Generate a single image from text prompt with optional reference images.

        Args:
            prompt: Text description of what to generate
            reference_images: Optional list of PIL Images as references (up to 14)
            aspect_ratio: Image aspect ratio. Options: 1:1, 2:3, 3:2, 3:4, 4:3,
                         4:5, 5:4, 9:16, 16:9, 21:9
            image_size: DEPRECATED - not supported in current API version

        Returns:
            PIL Image object

        Raises:
            ValueError: If generation fails or no image in response
        """
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        logger.info(f"Config: aspect_ratio={aspect_ratio}, "
                   f"references={len(reference_images) if reference_images else 0}")

        # Build contents array
        contents = [prompt]

        # Add reference images
        if reference_images:
            if len(reference_images) > 14:
                logger.warning(f"Too many reference images ({len(reference_images)}), "
                              f"using first 14")
                reference_images = reference_images[:14]

            contents.extend(reference_images)

        # Configure generation
        # Note: image_size parameter not supported in current API version
        # Using aspect_ratio only
        config = types.GenerateImageConfig(
            aspect_ratio=aspect_ratio,
            number_of_images=1
        )

        try:
            # Call API - use generate_image, not generate_content
            response = self.client.models.generate_image(
                model=self.model,
                prompt=prompt,
                config=config
            )

            # Extract image from response
            # Response has .images attribute with GeneratedImage objects
            if response.images and len(response.images) > 0:
                generated_img = response.images[0]
                # GeneratedImage has .image attribute which is PIL Image
                image = generated_img.image
                logger.info(f"Image generated successfully: {image.size}")
                return image

            # No image in response
            raise ValueError("No image in API response")

        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            raise

    def generate_image_bytes(
        self,
        prompt: str,
        reference_images: list[PILImage.Image] = None,
        aspect_ratio: str = "1:1",
        image_size: str = "2K",
        format: str = "PNG"
    ) -> bytes:
        """
        Generate image and return as bytes.

        Args:
            prompt: Text description
            reference_images: Optional reference images
            aspect_ratio: Image aspect ratio
            image_size: Resolution
            format: Output format (PNG, JPEG)

        Returns:
            Image bytes
        """
        image = self.generate_image(
            prompt=prompt,
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )

        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format=format)
        return output.getvalue()

    @staticmethod
    def aspect_ratio_from_size(width: int, height: int) -> str:
        """
        Determine aspect ratio string from pixel dimensions.

        Args:
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Aspect ratio string (e.g., "1:1", "16:9")
        """
        ratio = width / height

        # Map to supported aspect ratios
        aspect_ratios = {
            1.0: "1:1",
            0.67: "2:3",
            1.5: "3:2",
            0.75: "3:4",
            1.33: "4:3",
            0.8: "4:5",
            1.25: "5:4",
            0.56: "9:16",
            1.78: "16:9",
            2.33: "21:9"
        }

        # Find closest match
        closest = min(aspect_ratios.keys(), key=lambda k: abs(k - ratio))
        return aspect_ratios[closest]


# Singleton instance
_imagen_client_instance = None


def get_imagen_client() -> ImagenClient:
    """Get or create singleton ImagenClient instance."""
    global _imagen_client_instance
    if _imagen_client_instance is None:
        _imagen_client_instance = ImagenClient()
    return _imagen_client_instance
