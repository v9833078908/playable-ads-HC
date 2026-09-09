"""
Error Classifier — Classifies errors and provides retry strategies for Orchestrator V2

Each error type gets a specific recovery strategy and max retries.
"""

import logging
import re
from enum import Enum
from typing import Optional

logger = logging.getLogger('ErrorClassifier')


class ErrorType(Enum):
    """Types of errors the orchestrator can encounter."""
    JS_SYNTAX = "js_syntax"
    REGRESSION = "regression"           # Score dropped after patch
    PLAYWRIGHT_CRASH = "playwright_crash"
    PLAYWRIGHT_TIMEOUT = "playwright_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_CONTEXT_OVERFLOW = "llm_context_overflow"
    VISION_UNCLEAR = "vision_unclear"
    ASSET_FAILED = "asset_failed"
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """How to recover from each error type."""
    AUTOFIX = "autofix"             # Fix via separate LLM call
    ROLLBACK = "rollback"           # Revert to previous version
    RESTART_BROWSER = "restart_browser"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    COMPACT_HISTORY = "compact_history"
    RETRY_SIMPLIFIED = "retry_simplified"
    RETRY_WITH_PLACEHOLDER = "retry_with_placeholder"
    RETRY = "retry"


# Error classification rules
ERROR_RULES = [
    # JS syntax errors
    {
        "type": ErrorType.JS_SYNTAX,
        "patterns": [
            r"SyntaxError",
            r"Unexpected token",
            r"Unexpected end of input",
            r"Missing .* before",
            r"Unterminated string",
            r"Invalid or unexpected token",
        ],
        "strategy": RetryStrategy.AUTOFIX,
        "max_retries": 2,
    },
    # Score regression
    {
        "type": ErrorType.REGRESSION,
        "patterns": [
            r"score.*(dropped|decreased|regress)",
            r"regression",
            r"score.*lower.*than.*previous",
        ],
        "strategy": RetryStrategy.ROLLBACK,
        "max_retries": 1,
    },
    # Playwright crashes
    {
        "type": ErrorType.PLAYWRIGHT_CRASH,
        "patterns": [
            r"browser.*closed",
            r"Target.*closed",
            r"Protocol error",
            r"Connection.*refused",
            r"Browser.*disconnected",
        ],
        "strategy": RetryStrategy.RESTART_BROWSER,
        "max_retries": 2,
    },
    # Playwright timeouts (likely infinite JS loop)
    {
        "type": ErrorType.PLAYWRIGHT_TIMEOUT,
        "patterns": [
            r"Timeout.*exceeded",
            r"page.*timeout",
            r"Navigation.*timeout",
            r"waiting.*timeout",
        ],
        "strategy": RetryStrategy.ROLLBACK,
        "max_retries": 1,
    },
    # LLM rate limits
    {
        "type": ErrorType.LLM_RATE_LIMIT,
        "patterns": [
            r"rate.?limit",
            r"429",
            r"Too Many Requests",
            r"quota.*exceeded",
            r"ResourceExhausted",
        ],
        "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
        "max_retries": 3,
    },
    # LLM context overflow
    {
        "type": ErrorType.LLM_CONTEXT_OVERFLOW,
        "patterns": [
            r"context.*too.*large",
            r"maximum.*context.*length",
            r"token.*limit.*exceeded",
            r"prompt.*too.*long",
        ],
        "strategy": RetryStrategy.COMPACT_HISTORY,
        "max_retries": 1,
    },
    # Gemini Vision unclear response
    {
        "type": ErrorType.VISION_UNCLEAR,
        "patterns": [
            r"scores.*missing",
            r"all.*scores.*zero",
            r"vision.*failed",
            r"cannot.*parse.*vision",
            r"Gemini.*error",
        ],
        "strategy": RetryStrategy.RETRY_SIMPLIFIED,
        "max_retries": 2,
    },
    # Asset generation failed
    {
        "type": ErrorType.ASSET_FAILED,
        "patterns": [
            r"asset.*generat.*fail",
            r"FAL.*error",
            r"image.*generat.*fail",
            r"fal.*timeout",
        ],
        "strategy": RetryStrategy.RETRY_WITH_PLACEHOLDER,
        "max_retries": 2,
    },
]

# Backoff delays in seconds per retry attempt
BACKOFF_DELAYS = [5, 15, 45]


def classify_error(error: str | Exception) -> dict:
    """
    Classify an error and return its type, strategy, and max retries.

    Args:
        error: Error string or Exception

    Returns:
        {
            "type": ErrorType,
            "strategy": RetryStrategy,
            "max_retries": int,
            "message": str,
        }
    """
    error_str = str(error)

    for rule in ERROR_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, error_str, re.IGNORECASE):
                result = {
                    "type": rule["type"],
                    "strategy": rule["strategy"],
                    "max_retries": rule["max_retries"],
                    "message": error_str[:200],
                }
                logger.info(f"Classified error as {rule['type'].value}: {error_str[:100]}")
                return result

    # Unknown error
    logger.warning(f"Unknown error type: {error_str[:100]}")
    return {
        "type": ErrorType.UNKNOWN,
        "strategy": RetryStrategy.RETRY,
        "max_retries": 1,
        "message": error_str[:200],
    }


def get_backoff_delay(attempt: int) -> float:
    """Get exponential backoff delay for a given attempt (0-based)."""
    if attempt < len(BACKOFF_DELAYS):
        return BACKOFF_DELAYS[attempt]
    return BACKOFF_DELAYS[-1] * (2 ** (attempt - len(BACKOFF_DELAYS) + 1))


def should_retry(error_info: dict, current_attempt: int) -> bool:
    """Check if we should retry based on error info and current attempt."""
    return current_attempt < error_info["max_retries"]
