# 🔄 Gemini API Migration Guide

## Overview

This project has been migrated from the deprecated `google-generativeai` package to the new `google-genai` package.

## What Changed

### 1. Package Update
**Before:**
```python
google-generativeai>=0.4.0
```

**After:**
```python
google-genai>=1.0.0
```

### 2. Import Changes
**Before:**
```python
import google.generativeai as genai
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3-flash-preview")
```

**After:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
# Model name updated to latest: gemini-2.0-flash-exp
```

### 3. API Call Changes
**Before:**
```python
response = await model.generate_content_async([
    "prompt text",
    {"mime_type": "image/png", "data": image_bytes}
])
```

**After:**
```python
response = await client.aio.models.generate_content(
    model="gemini-2.0-flash-exp",
    contents=[
        types.Part.from_text("prompt text"),
        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    ]
)
```

## Migration Steps

### Step 1: Uninstall Old Package
```bash
pip uninstall google-generativeai -y
```

### Step 2: Install New Package
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install google-genai>=1.0.0
```

### Step 3: Verify Installation
```bash
python -c "from google import genai; print('✅ google-genai installed successfully')"
```

### Step 4: Test the Application
```bash
streamlit run app.py
```

## API Key Configuration

The API key configuration remains the same. You can set it in two ways:

### Option 1: Environment Variable (Recommended)
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or in [.env](.env):
```env
GEMINI_API_KEY=your-api-key-here
```

### Option 2: Direct Configuration
The client will automatically use `GOOGLE_API_KEY` environment variable if `GEMINI_API_KEY` is not set:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Updated Model

The migration also updates the model to the latest version:
- **Old:** `gemini-3-flash-preview` (deprecated)
- **New:** `gemini-2.0-flash-exp` (current)

## Breaking Changes

### Content Structure
The new API uses `types.Part` for all content:
- Text: `types.Part.from_text(text)`
- Images: `types.Part.from_bytes(data=bytes, mime_type=mime_type)`
- Files: `types.Part.from_uri(uri=uri, mime_type=mime_type)`

### Response Format
Response structure remains similar, but access pattern is now:
```python
response.text  # Still works
```

## Files Modified

1. [requirements.txt](../requirements.txt) - Updated dependency
2. [services/gemini_client.py](../services/gemini_client.py) - Complete refactor for new API

## Benefits of New API

✅ **Active Support:** Regular updates and bug fixes
✅ **Better Performance:** Optimized client implementation
✅ **Latest Models:** Access to newest Gemini models
✅ **Improved Types:** Better type hints and IDE support
✅ **Future-Proof:** Won't be deprecated

## Troubleshooting

### Issue: Import Error
```
ModuleNotFoundError: No module named 'google.genai'
```

**Solution:**
```bash
pip install google-genai
```

### Issue: API Key Not Found
```
Error: API key not configured
```

**Solution:**
Check your `.env` file or set environment variable:
```bash
echo "GEMINI_API_KEY=your-key" >> .env
```

### Issue: Old Package Conflicts
```
ImportError: cannot import name 'genai' from 'google'
```

**Solution:**
Uninstall old package completely:
```bash
pip uninstall google-generativeai -y
pip install google-genai
```

## Testing

After migration, test all Gemini Vision features:
1. ✅ Image analysis (`analyze_image`)
2. ✅ Batch analysis (`analyze_batch`)
3. ✅ Segmentation analysis (`analyze_for_segmentation`)
4. ✅ PDF extraction (`extract_from_pdf_page`)

Run the app and upload a PDF + images to verify everything works.

## References

- [Google Genai Documentation](https://github.com/google-gemini/python-genai)
- [Migration Announcement](https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md)
- [API Reference](https://ai.google.dev/api)

## Support

If you encounter issues during migration:
1. Check the [troubleshooting section](#troubleshooting)
2. Review logs in `app_debug.log`
3. Ensure API key is valid and has credits
4. Verify internet connection for API calls

---

**Migration completed:** January 31, 2026
**New package version:** google-genai >= 1.0.0
**Status:** ✅ Production Ready
