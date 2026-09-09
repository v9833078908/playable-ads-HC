# 🧪 Test Suite

This directory contains test scripts for the Playable Ads Generator project.

## Test Files

### Scene Management
- **[test_scene_detection.py](test_scene_detection.py)** - Tests for scene detection from brief
- **[test_scene_card_ui.py](test_scene_card_ui.py)** - UI component tests for scene cards

### Question & Answer System
- **[test_question_generator.py](test_question_generator.py)** - Question generation logic tests
- **[test_answer_processing.py](test_answer_processing.py)** - Answer processing and validation tests

### Orchestrator
- **[test_orchestrator_methods.py](test_orchestrator_methods.py)** - Core orchestrator method tests
- **[test_orchestrator_integration.py](test_orchestrator_integration.py)** - Full integration tests

### UI Components
- **[test_chat_interface.py](test_chat_interface.py)** - Chat interface tests
- **[test_progress_indicators.py](test_progress_indicators.py)** - Progress tracking UI tests
- **[test_confirmation_screen.py](test_confirmation_screen.py)** - Scenario confirmation screen tests

### Validation
- **[test_validation.py](test_validation.py)** - Scene and spec validation tests

## Running Tests

### Run All Tests
```bash
python -m pytest tests/
```

### Run Specific Test File
```bash
python -m pytest tests/test_scene_detection.py
```

### Run with Verbose Output
```bash
python -m pytest tests/ -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=playable_agents --cov=models --cov=tools
```

## Test Structure

Each test file follows this pattern:
```python
import pytest
from playable_agents.module import Component

def test_feature_name():
    # Arrange
    component = Component()

    # Act
    result = component.method()

    # Assert
    assert result == expected
```

## Dependencies

Tests may require additional packages:
```bash
pip install pytest pytest-asyncio pytest-cov
```

## Notes

- All tests are independent and can run in any order
- Tests use mock data and don't require real API keys
- Some tests may require Streamlit testing utilities

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Name test files as `test_<feature>.py`
3. Keep tests isolated and fast
4. Document complex test scenarios

---

**Last updated:** January 31, 2026
