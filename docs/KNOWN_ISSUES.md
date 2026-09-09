# Known Issues

## 🐛 HTML Generation Issues

### Problem: Generated HTML is Empty/Incomplete

**Date:** 2026-02-08
**Severity:** 🔴 Critical
**Status:** ⚠️ Needs Fix

#### Description
При запуске full pipeline с реальными данными (TZ_SNB_Car.md + Assets/PNG), Generator Agent успешно создает HTML файл, но он получается **неполным**:

- Файл обрезан на середине
- Отсутствуют закрывающие теги: `</script>`, `</body>`, `</html>`
- HTML не валидный и не открывается в браузере

#### Root Cause
Generator Agent (Claude Sonnet 4.5) достигает **лимита токенов** (max_tokens=16,000) при генерации HTML с большими base64-encoded ассетами.

**Проблема:**
- 16 ассетов в base64 занимают ~45KB
- При генерации HTML, base64 строки включаются в prompt
- Claude достигает лимита токенов и обрывает вывод

#### Impact
- ❌ HTML файл не работает
- ❌ Не проходит валидация
- ❌ Не открывается в браузере
- ⚠️ Temporary fix: вручную добавлены закрывающие теги

#### Technical Details

**Generator Agent Code:**
```python
# playable_agents/generator_agent.py:120
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=16000,  # ← TOO LOW for large assets
    messages=[{"role": "user", "content": user_prompt}],
    system=system_prompt
)
```

**Asset Manifest Size:**
- 6 reference assets: ~610 KB (base64)
- 10 generated assets: ~estimated 200-400 KB (base64)
- Total in JSON: ~800 KB - 1 MB

**Token Calculation:**
- ~1 token ≈ 4 chars
- 1 MB base64 ≈ 250,000 tokens
- Claude output max_tokens=16,000 is insufficient

#### Solution Options

### 🎯 Option 1: Increase max_tokens (Quick Fix)
```python
max_tokens=100000  # Increase to 100K
```
**Pros:** Simple, fast
**Cons:** May hit model limits, expensive

### 🎯 Option 2: Compress Assets Before Generation
```python
# Compress images before base64 encoding
from PIL import Image

def compress_image(img_bytes, max_size_kb=50):
    img = Image.open(BytesIO(img_bytes))
    # Resize if needed
    if img.width > 512:
        ratio = 512 / img.width
        new_size = (512, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # Save with lower quality
    output = BytesIO()
    img.save(output, format='PNG', optimize=True, quality=70)
    return output.getvalue()
```
**Pros:** Reduces token usage, faster generation
**Cons:** Lower asset quality

### 🎯 Option 3: Template-Based Generation (Recommended)
Instead of generating full HTML with LLM, use **templates**:

```python
# 1. Generate only game logic code (not full HTML)
game_logic = claude.generate("""
Create game logic JavaScript for car wash game:
- Touch event handlers
- Progress tracking
- State management
NO HTML structure, ONLY JavaScript code
""")

# 2. Inject into template
html = template.render(
    game_logic=game_logic,
    assets=asset_manifest,  # Injected at runtime
    store_url=store_url
)
```

**Pros:**
- ✅ Predictable output size
- ✅ Faster generation (only logic, not structure)
- ✅ Better control over HTML structure
- ✅ Easier to debug

**Cons:**
- Requires creating templates per genre

### 🎯 Option 4: Two-Pass Generation
```python
# Pass 1: Generate HTML structure (no assets)
html_structure = claude.generate("Generate HTML structure...")

# Pass 2: Inject assets client-side
html_final = inject_assets(html_structure, asset_manifest)
```

#### Immediate Action Required

1. **Short-term fix (DONE):**
   - ✅ Manually added closing tags to make HTML valid
   - ⚠️ File works but still has 5 major QA issues

2. **Medium-term fix (TODO):**
   - [ ] Implement Option 3 (Template-Based Generation)
   - [ ] Create templates for car-wash genre
   - [ ] Test with full asset manifest

3. **Long-term fix (TODO):**
   - [ ] Implement asset compression pipeline
   - [ ] Add automatic quality adjustment based on file size
   - [ ] Create fallback mechanism if generation fails

#### Related Issues

**QA Issues Found:**
1. ❌ Missing touchstart event handler
2. ❌ Missing touchmove event handler
3. ❌ Missing touchend event handler
4. ❌ No platform detection (iOS/Android)
5. ❌ Missing requestAnimationFrame game loop

These issues suggest Generator Agent didn't complete full implementation due to token limit.

#### Testing

**To reproduce:**
```bash
cd playable-ads-hackathon
source venv/bin/activate
python test_real_pipeline.py
```

**Expected:** Complete HTML with all features
**Actual:** Truncated HTML, missing closing tags and features

#### Priority

🔴 **P0 - Critical**

This blocks production use of the pipeline. Must be fixed before release.

---

**Last Updated:** 2026-02-08
**Assigned To:** TBD
**See Also:**
- [PIPELINE_TEST_RESULTS.txt](PIPELINE_TEST_RESULTS.txt)
- [AGENT_OUTPUT_REPORT.md](../AGENT_OUTPUT_REPORT.md)
