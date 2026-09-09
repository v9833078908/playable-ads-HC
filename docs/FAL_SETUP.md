# FAL.AI Setup Guide for Asset Generation

## Overview

This project uses [FAL.AI](https://fal.ai) to access Gemini 2.5 Flash Image generation for creating playable ad assets.

## Prerequisites

1. **FAL.AI Account**: Sign up at https://fal.ai
2. **API Key**: Get your key from https://fal.ai/dashboard/keys

## Setup Steps

### 1. Get FAL API Key

1. Go to https://fal.ai and sign up/login
2. Navigate to https://fal.ai/dashboard/keys
3. Create a new API key
4. Copy the key (starts with `FAL_KEY_...` or similar)

### 2. Add to Environment

Add your FAL API key to `.env` file:

```bash
# .env
FAL_KEY=your_fal_api_key_here
```

**Example:**
```bash
FAL_KEY=FAL_KEY_abc123xyz456
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fal-client>=0.12.0` - FAL.AI Python SDK
- `requests>=2.31.0` - For downloading generated images

### 4. Test the Setup

Run the test script to verify everything works:

```bash
python test_fal_imagen.py
```

**Expected output:**
```
============================================================
🧪 FAL.AI GEMINI IMAGE GENERATION TEST SUITE
============================================================

✅ FAL_KEY found: FAL_KEY_abc123...
✅ Client initialized
📝 Prompt: A cartoon blue knight character...
⏳ Generating image (this may take 10-30 seconds)...
✅ SUCCESS!
   Image size: (1024, 1024)
   Saved to: test_fal_output_basic.png
```

## Usage

### Basic Image Generation

```python
from services.fal_imagen_client import FALImagenClient

# Initialize client
client = FALImagenClient()  # Uses FAL_KEY from env

# Generate image
image = client.generate_image(
    prompt="A cartoon blue knight in shiny armor",
    aspect_ratio="1:1",
    output_format="png"
)

# Save
image.save("output.png")
```

### With Reference Images (Edit Mode)

```python
# Generate with style reference
image = client.generate_with_reference(
    prompt="Make this character more cartoonish",
    reference_image_url="https://example.com/reference.png",
    aspect_ratio="1:1"
)
```

## API Details

### Model
- **Name**: `gemini-25-flash-image`
- **Provider**: FAL.AI (accessing Google Gemini)
- **Pricing**: ~$0.039 per image (25 images per $1)

### Parameters

| Parameter | Type | Options | Default |
|-----------|------|---------|---------|
| `prompt` | string | 3-50,000 chars | required |
| `aspect_ratio` | string | 1:1, 16:9, 4:3, etc | "1:1" |
| `num_images` | int | 1-4 | 1 |
| `output_format` | string | png, jpeg, webp | "png" |

### Supported Aspect Ratios
- Square: `1:1`
- Landscape: `21:9`, `16:9`, `3:2`, `4:3`, `5:4`
- Portrait: `4:5`, `3:4`, `2:3`, `9:16`

## Integration with Asset Generator

The FAL.AI client is integrated into `playable_agents/asset_generator.py`:

```python
from services.fal_imagen_client import get_fal_imagen_client

# Get singleton client
client = get_fal_imagen_client()

# Generate assets
for asset in assets_plan:
    prompt = build_prompt(asset, brief_style)

    image_bytes = client.generate_image_bytes(
        prompt=prompt,
        aspect_ratio=ROLE_TEMPLATES[asset["role"]]["aspect_ratio"]
    )

    # Postprocess...
```

## Troubleshooting

### Error: "FAL API key not found"

**Solution:** Ensure FAL_KEY is set in `.env`:
```bash
echo "FAL_KEY=your_key" >> .env
```

### Error: "401 Unauthorized"

**Cause:** Invalid or expired API key

**Solution:**
1. Verify key at https://fal.ai/dashboard/keys
2. Create new key if needed
3. Update `.env` file

### Error: "429 Too Many Requests"

**Cause:** Rate limit exceeded

**Solution:**
- Wait a few seconds between requests
- Check your FAL.AI dashboard for quota limits
- Consider upgrading plan if needed

### Slow Generation (>60 seconds)

**Normal:** Image generation takes 10-30 seconds typically

**If consistently slow:**
- Check FAL.AI status page
- Try reducing prompt complexity
- Use smaller aspect ratios

## Cost Estimation

### For Playable Ad Generation

Typical playable ad needs:
- 5-10 assets (characters, backgrounds, UI elements)
- Cost: ~$0.20-$0.40 per playable

**Example:**
```
7 assets × $0.039 = ~$0.27 per playable
100 playables × $0.27 = ~$27
```

### Best Practices for Cost Optimization

1. **Reuse assets** across similar playables
2. **Use appropriate aspect ratios** (smaller = faster/cheaper sometimes)
3. **Batch generation** when possible
4. **Test with small prompts** first

## Support

- **FAL.AI Docs**: https://docs.fal.ai
- **FAL.AI Discord**: https://discord.gg/fal-ai
- **Gemini Image Docs**: https://ai.google.dev/gemini-api/docs/image-generation

---

**Last Updated:** 2026-02-01
**FAL SDK Version:** 0.12.0
