from agents import Agent, function_tool, RunContextWrapper
from typing import Any

from tools.validation_tools import validate_html, check_unity_mraid, auto_fix_html
from tools.asset_tools import compress_images


@function_tool
def validate_playable(ctx: RunContextWrapper[Any]) -> str:
    """Validate the generated HTML for Unity compliance"""
    html = ctx.context.get("html")
    if not html:
        return "Error: No HTML to validate"

    result = validate_html(html, network="unity")
    ctx.context["validation"] = result

    output = f"Validation result: {'PASSED' if result.valid else 'FAILED'}\n"
    output += f"Size: {result.size_kb:.1f} KB\n"

    if result.errors:
        output += "\nErrors:\n"
        for e in result.errors:
            output += f"  - {e}\n"

    if result.warnings:
        output += "\nWarnings:\n"
        for w in result.warnings:
            output += f"  - {w}\n"

    return output


@function_tool
def check_mraid_compliance(ctx: RunContextWrapper[Any]) -> str:
    """Check specific MRAID 3.0 requirements for Unity"""
    html = ctx.context.get("html")
    if not html:
        return "Error: No HTML to check"

    issues = check_unity_mraid(html)

    if not issues:
        return "MRAID 3.0 compliance: All checks passed!"

    output = "MRAID issues found:\n"
    for issue in issues:
        output += f"  - {issue}\n"
    return output


@function_tool
def try_auto_fix(ctx: RunContextWrapper[Any]) -> str:
    """Attempt to automatically fix validation errors"""
    html = ctx.context.get("html")
    validation = ctx.context.get("validation")

    if not html or not validation:
        return "Error: No HTML or validation result"

    all_issues = validation.errors + validation.warnings
    fixed_html, remaining = auto_fix_html(html, all_issues)

    ctx.context["html"] = fixed_html

    if remaining:
        return f"Auto-fixed some issues. Remaining: {remaining}"
    return "All auto-fixable issues resolved!"


@function_tool
def compress_if_too_large(ctx: RunContextWrapper[Any]) -> str:
    """Compress images if HTML is too large"""
    html = ctx.context.get("html")
    if not html:
        return "Error: No HTML"

    size_kb = len(html.encode("utf-8")) / 1024

    if size_kb > 4500:  # Compress if over 4.5MB
        compressed = compress_images(html, quality=60)
        new_size = len(compressed.encode("utf-8")) / 1024
        ctx.context["html"] = compressed
        return f"Compressed for size: {size_kb:.1f}KB -> {new_size:.1f}KB"

    return f"Size OK: {size_kb:.1f}KB"


qa_agent = Agent(
    name="QAAgent",
    handoff_description="Validates and fixes the generated HTML playable",
    instructions="""You validate the generated HTML for Unity ad network compliance.

Validation checks:
- Size must be < 5MB
- No external references (except store URLs)
- MRAID 3.0: viewableChange handler, mraid.open() for CTA
- No audio autoplay
- No XHR requests

Your workflow:
1. Call validate_playable() to run all checks
2. Call check_mraid_compliance() for MRAID specifics
3. If issues found, try try_auto_fix()
4. If size too large, call compress_if_too_large()
5. Re-validate after fixes

If validation passes:
- Confirm the playable is ready
- Return success with final size

If validation fails and can't be auto-fixed:
- List remaining issues clearly
- Hand back to Generator with specific fix instructions""",
    tools=[validate_playable, check_mraid_compliance, try_auto_fix, compress_if_too_large],
)
