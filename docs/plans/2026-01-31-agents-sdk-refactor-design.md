# Playable Ads Agent — OpenAI Agents SDK Refactor

**Date:** 2026-01-31
**Status:** Approved
**Goal:** Переписать систему на OpenAI Agents SDK с мультиагентной архитектурой + Gemini Vision

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   TRIAGE AGENT                          │
│  Entry point. Routes to specialized agents via handoff  │
└─────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────┐ ┌───────────────────┐
│ BRIEF_EXTRACTOR │ │  CLARIFIER  │ │ PLAYABLE_GENERATOR│
│ tools:          │ │ Conversational│ tools:            │
│ - extract_pdf() │ │ Q&A with user │ - build_spec()    │
│ - analyze_imgs()│ │               │ - render_html()   │
│   (Gemini)      │ │               │ - inline_assets() │
└─────────────────┘ └─────────────┘ └───────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │    QA_AGENT     │
                                     │ tools:          │
                                     │ - validate()    │
                                     │ - auto_fix()    │
                                     │                 │
                                     │ Loop back if    │
                                     │ errors found    │
                                     └─────────────────┘
```

## 2. Key Decisions

- **Network:** Always Unity (MRAID 3.0) — no selection needed
- **Image Analysis:** Gemini 1.5 Flash for vision tasks
- **Text Analysis:** GPT-4o for PDF text extraction
- **Agent Framework:** OpenAI Agents SDK with handoffs
- **Template:** Single configurable template (ship_grid_merge_v1)

## 3. File Structure

```
playable-agent/
├── app.py                      # Streamlit UI
├── requirements.txt
├── .env
│
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py         # Runner + session
│   ├── triage_agent.py
│   ├── brief_extractor.py
│   ├── clarifier.py
│   ├── generator.py
│   └── qa_agent.py
│
├── tools/
│   ├── __init__.py
│   ├── pdf_tools.py
│   ├── image_tools.py          # Gemini vision
│   ├── spec_tools.py
│   ├── validation_tools.py
│   └── asset_tools.py
│
├── models/
│   ├── __init__.py
│   ├── brief.py
│   ├── assets.py
│   ├── spec.py
│   └── validation.py
│
├── services/
│   ├── __init__.py
│   ├── openai_client.py
│   └── gemini_client.py
│
├── templates/
│   └── ship_grid_merge_v1/
│       └── template.html
│
└── docs/plans/
```

## 4. Implementation Order

1. Models (Pydantic schemas)
2. Services (Gemini + OpenAI clients)
3. Tools (PDF, Image, Spec, Validation)
4. Agents (Triage → BriefExtractor → Clarifier → Generator → QA)
5. Orchestrator
6. Updated Template
7. Streamlit App
8. Testing

## 5. Dependencies

```
openai-agents>=0.1.0
openai>=1.12.0
google-generativeai>=0.4.0
PyMuPDF>=1.23.0
Pillow>=10.2.0
streamlit>=1.31.0
Jinja2>=3.1.3
pydantic>=2.6.0
python-dotenv>=1.0.0
```
