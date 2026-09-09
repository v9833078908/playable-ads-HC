"""FAL.AI Imagen client for generating visual assets using Gemini 2.5 Flash Image"""

import os
import logging
from typing import Optional, List
from PIL import Image as PILImage
import io
import base64
import requests

import fal_client

logger = logging.getLogger(__name__)


class FALImagenClient:
    """
    Client for FAL.AI Gemini 2.5 Flash Image Generation API.

    Uses FAL.AI platform to access Gemini image generation.
    Documentation: https://fal.ai/models/fal-ai/gemini-25-flash-image
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FAL Imagen client.

        Args:
            api_key: FAL API key. If not provided, uses FAL_KEY env var.
        """
        self.api_key = api_key or os.getenv("FAL_KEY")

        if not self.api_key:
            raise ValueError(
                "FAL API key not found. Set FAL_KEY environment variable "
                "or pass api_key parameter."
            )

        # Configure FAL client
        os.environ["FAL_KEY"] = self.api_key

        # Model endpoint
        self.model = "fal-ai/gemini-25-flash-image"

        logger.info(f"FALImagenClient initialized with model: {self.model}")

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        num_images: int = 1,
        output_format: str = "png"
    ) -> PILImage.Image:
        """
        Generate a single image from text prompt.

        Args:
            prompt: Text description of what to generate (3-50,000 chars)
            aspect_ratio: Image aspect ratio. Options:
                         "21:9", "16:9", "3:2", "4:3", "5:4", "1:1",
                         "4:5", "3:4", "2:3", "9:16"
            num_images: Number of images to generate (1-4). Returns first.
            output_format: Output format: "png", "jpeg", "webp"

        Returns:
            PIL Image object

        Raises:
            ValueError: If generation fails
        """
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        logger.info(f"Config: aspect_ratio={aspect_ratio}, format={output_format}")

        try:
            # Call FAL API
            result = fal_client.subscribe(
                self.model,
                arguments={
                    "prompt": prompt,
                    "num_images": num_images,
                    "aspect_ratio": aspect_ratio,
                    "output_format": output_format,
                    "sync_mode": False  # Use async mode for better reliability
                },
                with_logs=True
            )

            # Extract image from response
            if result and "images" in result and len(result["images"]) > 0:
                image_data = result["images"][0]
                image_url = image_data["url"]

                logger.info(f"Image generated: {image_url}")
                logger.info(f"Size: {image_data.get('width')}x{image_data.get('height')}")

                # Download image
                response = requests.get(image_url)
                response.raise_for_status()

                image = PILImage.open(io.BytesIO(response.content))
                logger.info(f"Image loaded successfully: {image.size}")
                return image

            # No image in response
            raise ValueError("No images in FAL API response")

        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            raise

    def generate_image_bytes(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        format: str = "PNG"
    ) -> bytes:
        """
        Generate image and return as bytes.

        Args:
            prompt: Text description
            aspect_ratio: Image aspect ratio
            format: Output format (PNG, JPEG)

        Returns:
            Image bytes
        """
        image = self.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            output_format=format.lower()
        )

        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format=format.upper())
        return output.getvalue()

    def generate_with_reference(
        self,
        prompt: str,
        reference_image_url: str,
        aspect_ratio: str = "1:1",
        output_format: str = "png"
    ) -> PILImage.Image:
        """
        Generate image using edit endpoint with reference image.

        Args:
            prompt: Editing instructions
            reference_image_url: URL of reference image (must be publicly accessible)
            aspect_ratio: Image aspect ratio
            output_format: Output format

        Returns:
            PIL Image object
        """
        logger.info(f"Generating with reference: {reference_image_url}")
        logger.info(f"Edit prompt: {prompt[:50]}...")

        try:
            # Use edit endpoint
            result = fal_client.subscribe(
                f"{self.model}/edit",
                arguments={
                    "prompt": prompt,
                    "image_urls": [reference_image_url],
                    "num_images": 1,
                    "aspect_ratio": aspect_ratio,
                    "output_format": output_format
                },
                with_logs=True
            )

            # Extract image
            if result and "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]

                logger.info(f"Edited image generated: {image_url}")

                # Download
                response = requests.get(image_url)
                response.raise_for_status()

                image = PILImage.open(io.BytesIO(response.content))
                return image

            raise ValueError("No images in edit response")

        except Exception as e:
            logger.error(f"Image edit failed: {e}", exc_info=True)
            raise

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
_fal_imagen_client_instance = None


def get_fal_imagen_client() -> FALImagenClient:
    """Get or create singleton FALImagenClient instance."""
    global _fal_imagen_client_instance
    if _fal_imagen_client_instance is None:
        _fal_imagen_client_instance = FALImagenClient()
    return _fal_imagen_client_instance
