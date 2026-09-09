# TODO: Pipeline Fixes

## 🔴 P0 - Critical (Blocking Production)

### 1. Fix HTML Generation Token Limit
**Issue:** Generator Agent hits 16K token limit, HTML truncated
**Location:** `playable_agents/generator_agent.py:120`
**Options:**
- [ ] Option A: Increase max_tokens to 100K
- [ ] Option B: Implement template-based generation (RECOMMENDED)
- [ ] Option C: Two-pass generation (structure + assets)

**Estimated time:** 4-6 hours
**Priority:** ASAP

### 2. Implement Missing Core Features
**Issue:** Generated HTML missing essential functionality
**Features needed:**
- [ ] Touch event handlers (touchstart/move/end)
- [ ] requestAnimationFrame game loop
- [ ] Platform detection (iOS/Android for store URLs)

**Estimated time:** 3-4 hours
**Priority:** Before first deployment

---

## 🟡 P1 - High Priority

### 3. QA-Iteration Loop
**Issue:** No automatic fixing of QA issues
**Tasks:**
- [ ] Implement QA-iteration agent
- [ ] Add max 5 iterations with feedback loop
- [ ] Test with Generator Agent improvements

**Estimated time:** 6-8 hours

### 4. Visual QA Agent
**Issue:** No visual validation of generated HTML
**Tasks:**
- [ ] Add Playwright screenshot capture
- [ ] Implement Gemini Vision analysis
- [ ] Check for visual bugs, layout issues

**Estimated time:** 4-6 hours

### 5. Asset Compression Pipeline
**Issue:** Large base64 assets cause token limit problems
**Tasks:**
- [ ] Add PIL-based image compression
- [ ] Auto-resize images > 512px
- [ ] Target max 50KB per asset
- [ ] Quality adjustment based on file size

**Estimated time:** 3-4 hours

---

## 🟢 P2 - Medium Priority

### 6. Template System
**Issue:** LLM generation unpredictable, slow, expensive
**Tasks:**
- [ ] Create Jinja2 templates for each genre
- [ ] car-wash template
- [ ] merge-2 template  
- [ ] puzzle template
- [ ] LLM generates only game logic, not structure

**Estimated time:** 8-10 hours per template

### 7. Error Handling & Retry Logic
**Issue:** No fallback when generation fails
**Tasks:**
- [ ] Add try/catch with retries (max 3)
- [ ] Fallback to simpler generation if complex fails
- [ ] Store failed generations for debugging

**Estimated time:** 2-3 hours

### 8. Testing Suite
**Issue:** No automated tests for pipeline
**Tasks:**
- [ ] Unit tests for each agent
- [ ] Integration test for full pipeline
- [ ] Test with multiple TZ examples
- [ ] Mock FAL API for faster tests

**Estimated time:** 6-8 hours

---

## 🔵 P3 - Low Priority (Nice to Have)

### 9. Performance Optimization
**Tasks:**
- [ ] Cache FAL API responses (same prompts)
- [ ] Parallel asset generation (batch requests)
- [ ] Reduce scenario agent processing time

**Estimated time:** 4-6 hours

### 10. Multi-Language Support
**Tasks:**
- [ ] Support more languages (EN, ES, DE, FR, ZH)
- [ ] Auto-detect language from TZ
- [ ] Translate UI texts if needed

**Estimated time:** 3-4 hours

### 11. Analytics & Monitoring
**Tasks:**
- [ ] Track generation success rate
- [ ] Monitor token usage per agent
- [ ] Alert on failures
- [ ] Dashboard for metrics

**Estimated time:** 6-8 hours

---

## 📝 Notes

### Quick Wins
Start with P0 items:
1. Template-based generation (biggest impact)
2. Add missing touch events & RAF loop
3. Increase max_tokens as temporary fix

### Long-term Vision
- Template library for all genres
- Visual QA before delivery
- 95%+ success rate on generation
- <60s total pipeline time

### Dependencies
- P0.1 blocks all other work (fix token limit first)
- P1.3 depends on P0.2 (QA needs working HTML)
- P2.6 works alongside P0.1 (templates)

---

**Last Updated:** 2026-02-08
**See Also:**
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- [PIPELINE_TEST_SUMMARY.md](PIPELINE_TEST_SUMMARY.md)
