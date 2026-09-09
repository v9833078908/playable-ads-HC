from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of HTML validation"""
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    size_kb: float = 0
    network: str = "unity"


class UserAnswers(BaseModel):
    """Answers collected from user"""
    language: str = "EN"
    store_android: str = ""
    store_ios: str = ""
    asset_mappings: dict[str, str] = {}  # Manual overrides
