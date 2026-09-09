# 🎮 Playable Ads Generator - UX Flow

## Overview

The Playable Ads Generator features a clean, minimalist interface inspired by shadcn design principles. The workflow includes an intermediate scenario approval step that gives users full control over the generated playable specification before HTML generation.

## Design System

### Visual Style
- **Aesthetic**: Minimalist, shadcn-inspired
- **Color Palette**: Neutral zinc/slate tones
- **Typography**: Clean sans-serif with clear hierarchy
- **Components**: Subtle shadows, thin borders, smooth transitions
- **Layout**: Card-based design with generous spacing

### Theme Configuration
- Primary Color: `#18181b` (zinc-900)
- Background: `#ffffff` (white)
- Secondary Background: `#f8f9fa` (light gray)
- Border Radius: `0.5rem`

## User Flow

### 1. Upload Phase
**Step**: `upload`

- User uploads PDF specification and game asset images
- Sidebar displays thumbnails of uploaded images
- Clean file upload zones with hover states
- Start Analysis button triggers the workflow

### 2. Chat Phase
**Step**: `chat`

- AI agent analyzes uploaded files
- Interactive chat interface for clarification questions
- Quick action buttons for common choices:
  - 🇬🇧 English
  - 🇷🇺 Russian
  - 🚀 Generate Scenario
- Agent asks for missing information (store URLs, language, etc.)
- Progress tracked through conversation history

### 3. Scenario Approval Phase ✨ **NEW**
**Step**: `scenario_approval`

This is the new intermediate step where users review and approve the generated PlayableSpec before HTML generation.

#### UI Components

**Left Column (Main Content)**:
1. **Playable Information Card**
   - Title
   - Network (Unity, etc.)
   - Language

2. **Scenes Card**
   - List of all scenes with expandable details
   - Scene type (tutorial, battle, victory)
   - Background assets
   - Mechanics configuration
   - UI elements JSON

3. **Assets Card**
   - List of all images
   - Asset references
   - Preview of first 5 assets

**Right Column (Actions)**:
1. **✅ Approve & Generate HTML** (Primary Action)
   - Confirms the scenario
   - Triggers HTML generation
   - Returns to chat with generated HTML

2. **✏️ Edit Scenario**
   - Toggles JSON editor mode
   - Allows direct editing of PlayableSpec
   - Validation on save
   - Cancel option to discard changes

3. **🧠 Think Harder**
   - Asks AI to reconsider and improve the scenario
   - Analyzes mechanics, flow, and asset usage
   - Generates an enhanced version
   - Updates the scenario display

4. **💬 Back to Chat**
   - Returns to conversation
   - Scenario remains saved
   - Can continue asking questions

#### Edit Mode

When activated, shows:
- Full JSON editor with syntax highlighting (via textarea)
- Save Changes button (validates JSON structure)
- Cancel button (discards changes)
- Real-time validation feedback

#### Technical Details

**State Management**:
```python
st.session_state.spec          # Current PlayableSpec object
st.session_state.spec_text     # JSON string for editing
st.session_state.edit_mode     # Boolean for edit mode toggle
st.session_state.step          # Current workflow step
```

**Triggers**:
- Agent generates `spec` but not `html` → Navigate to `scenario_approval`
- User clicks "Approve" → Generate HTML, return to `chat`
- User clicks "Think Harder" → Reset `spec`, ask agent to regenerate
- User clicks "Edit" → Toggle `edit_mode`

### 4. HTML Generation & Download
**Step**: `chat` (with HTML available)

- HTML preview in expandable section
- Download button in sidebar and preview
- Validation metrics (file size, MRAID compliance)
- Start Over button to reset workflow

## Key Improvements

### 1. **Transparency**
Users can see exactly what will be generated before HTML creation:
- Scene structure
- Mechanics configuration
- Asset mapping
- UI elements

### 2. **Control**
Three levels of control:
- **Quick approval**: Trust the AI, generate immediately
- **Edit mode**: Fine-tune specific details
- **Think harder**: Get AI to reconsider the approach

### 3. **Iterative Refinement**
- No need to regenerate from scratch
- Edit specific parts of the spec
- Ask for improvements without losing progress

### 4. **Error Prevention**
- Review before expensive HTML generation
- Catch issues early (missing assets, wrong mechanics)
- Validate JSON structure in edit mode

## Technical Implementation

### CSS Architecture
- Custom CSS in `.streamlit/custom.css`
- CSS variables for consistent theming
- Hover states and transitions
- Card-based components
- Responsive layouts

### State Flow
```
Upload → process_files() → Chat → chat() →
  → build_spec() → Scenario Approval →
    → Approve → render_html() → Download
    → Edit → Save → Scenario Approval
    → Think Harder → build_spec() → Scenario Approval
```

### Agent Integration
The workflow leverages the multi-agent system:
1. **BriefExtractor**: Parses PDF, extracts requirements
2. **Clarifier**: Asks follow-up questions
3. **Generator**:
   - `build_spec()`: Creates PlayableSpec → **Approval step**
   - `render_html()`: Generates HTML (after approval)
4. **QA Agent**: Validates generated HTML

## Design Principles

### Minimalism
- Remove unnecessary elements
- Clear visual hierarchy
- Ample whitespace
- Focused attention

### Consistency
- Unified color scheme
- Consistent spacing (0.5rem base)
- Predictable button styles
- Standard border radius

### Feedback
- Loading states with spinners
- Success/error messages
- Hover states on interactive elements
- Smooth transitions (0.2s ease)

### Accessibility
- High contrast text
- Clear focus states
- Semantic HTML structure
- Keyboard navigation support

## Future Enhancements

### Potential Additions
1. **Visual Scenario Preview**: Render a mockup of the playable
2. **Comparison Mode**: Compare multiple scenario versions
3. **Templates**: Save and load scenario templates
4. **Collaboration**: Share scenarios for team review
5. **Version History**: Track scenario changes over time
6. **AI Suggestions**: Highlight potential improvements in the scenario

### Performance Optimizations
1. Lazy load scene details in expandable sections
2. Debounce JSON editor validation
3. Cache scenario renders
4. Progressive loading for large asset lists

## Conclusion

The new UX flow with scenario approval provides a perfect balance between automation and user control. Users can trust the AI for quick generation while having the tools to review, edit, and refine the output before committing to HTML generation.

The shadcn-inspired design creates a professional, modern interface that feels polished and intentional—a significant improvement over generic Streamlit styling.
