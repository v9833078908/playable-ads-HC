import re

from models import ValidationResult


def validate_html(html: str, network: str = "unity") -> ValidationResult:
    """Full validation for Unity network"""

    errors = []
    warnings = []
    size_kb = len(html.encode("utf-8")) / 1024

    # === SIZE CHECK ===
    if size_kb > 5000:
        errors.append(f"Size {size_kb:.0f}KB exceeds 5MB limit")
    elif size_kb > 4000:
        warnings.append(f"Size {size_kb:.0f}KB approaching limit")

    # === EXTERNAL REFERENCES ===
    external = re.findall(r'(?:src|href)=["\']https?://([^"\']+)', html)
    for ref in external:
        if "play.google.com" not in ref and "apps.apple.com" not in ref:
            errors.append(f"External reference: {ref[:50]}")

    # === MRAID 3.0 CHECKS (Unity) ===
    if "mraid" not in html.lower():
        errors.append("MRAID not found")

    if "viewableChange" not in html:
        errors.append("Missing viewableChange handler (Unity requires this)")

    if "mraid.getState" not in html:
        warnings.append("mraid.getState() not found")

    if "mraid.open" not in html:
        errors.append("mraid.open() required for CTA")

    # === FORBIDDEN PATTERNS ===
    if re.search(r"autoplay.*audio|audio.*autoplay", html, re.I):
        errors.append("Audio autoplay forbidden")

    if re.search(r"XMLHttpRequest|fetch\s*\(", html):
        warnings.append("XHR/Fetch detected - verify no external calls")

    if '<script src="http' in html or '<link href="http' in html:
        errors.append("External script/style references found")

    # === GOOD PATTERNS ===
    if "user-scalable=no" not in html:
        warnings.append("Consider adding user-scalable=no to viewport")

    if "touch-action" not in html:
        warnings.append("Consider adding touch-action CSS for mobile")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        size_kb=size_kb,
        network=network,
    )


def check_unity_mraid(html: str) -> list[str]:
    """Specific MRAID 3.0 checks for Unity"""
    issues = []

    # Must wait for viewableChange
    if not re.search(r"mraid\.addEventListener\s*\(\s*['\"]viewableChange['\"]", html):
        issues.append("Must add viewableChange listener before starting game")

    # Must check isViewable
    if "isViewable" not in html:
        issues.append("Should check mraid.isViewable() before start")

    # Proper ready check
    if not re.search(r"mraid\.getState\s*\(\s*\)\s*===?\s*['\"]loading['\"]", html):
        issues.append("Should check if mraid.getState() === 'loading'")

    # No auto-redirect
    if "location.href" in html or "location.replace" in html:
        issues.append("Auto-redirect forbidden - use mraid.open() only on user action")

    return issues


def auto_fix_html(html: str, errors: list[str]) -> tuple[str, list[str]]:
    """Attempt to auto-fix common issues"""

    fixed = html
    fixed_issues = []
    remaining = []

    for error in errors:
        error_lower = error.lower()

        if "user-scalable" in error_lower:
            # Fix viewport
            fixed = fixed.replace(
                "width=device-width, initial-scale=1.0",
                "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no",
            )
            fixed_issues.append("Added user-scalable=no")

        elif "viewablechange" in error_lower and "missing" in error_lower:
            if "viewableChange" in fixed:
                fixed_issues.append("viewableChange already present")
            else:
                remaining.append(error)

        elif "size" in error_lower:
            remaining.append(error + " (manual image compression needed)")

        else:
            remaining.append(error)

    return fixed, remaining
