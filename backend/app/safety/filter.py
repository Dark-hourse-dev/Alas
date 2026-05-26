"""
ALAS Safety Filter — Constitutional constraint checker.

Implements the Safety & Alignment Envelope from the blueprint.
Every output passes through constitutional checks before delivery.
"""

import re
import logging

from backend.app.config import get_settings

logger = logging.getLogger("alas.safety")


# Constitutional constraints — bright-line rules
BLOCKED_PATTERNS = [
    # Violence & harm
    r"\b(how to (?:make|build|create) (?:a )?(?:bomb|explosive|weapon))\b",
    r"\b(instructions? (?:for|to) (?:harm|kill|attack|poison))\b",

    # Self-harm guidance
    r"\b(methods? (?:of|for) (?:suicide|self.?harm))\b",

    # Personal data extraction
    r"\b((?:social security|credit card|bank account) number)\b",

    # Manipulation tactics
    r"\b(how to (?:manipulate|gaslight|blackmail|extort))\b",
]


class SafetyFilter:
    """
    Constitutional safety filter.
    
    Checks both inputs and outputs against constitutional constraints
    to prevent harmful content from being processed or delivered.
    """

    def __init__(self):
        self._enabled = get_settings().safety_enabled
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS
        ]

    def check_input(self, text: str) -> dict:
        """
        Check user input against safety constraints.
        
        Returns:
            Dictionary with 'safe' boolean and optional 'reason'.
        """
        if not self._enabled:
            return {"safe": True}

        return self._run_checks(text, direction="input")

    def check_output(self, text: str) -> dict:
        """
        Check AI output against safety constraints before delivery.
        
        Returns:
            Dictionary with 'safe' boolean and optional 'reason'.
        """
        if not self._enabled:
            return {"safe": True}

        return self._run_checks(text, direction="output")

    def _run_checks(self, text: str, direction: str = "input") -> dict:
        """Run all constitutional checks on the given text."""

        # Check 1: Pattern-based blocking
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                reason = f"Content matched a constitutional safety constraint ({direction})"
                logger.warning(f"Safety filter triggered: {reason}")
                return {
                    "safe": False,
                    "reason": reason,
                    "action": "blocked",
                }

        # Check 2: Excessive personal information detection (output only)
        if direction == "output":
            pii_result = self._check_pii_leakage(text)
            if not pii_result["safe"]:
                return pii_result

        return {"safe": True}

    def _check_pii_leakage(self, text: str) -> dict:
        """Check for potential PII leakage in output."""
        # Basic pattern checks for common PII formats
        pii_patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN-like pattern"),
            (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit card-like pattern"),
        ]

        for pattern, desc in pii_patterns:
            if re.search(pattern, text):
                logger.warning(f"PII leakage detected: {desc}")
                return {
                    "safe": False,
                    "reason": f"Potential PII leakage detected: {desc}",
                    "action": "blocked",
                }

        return {"safe": True}

    def get_safe_response(self, reason: str = "") -> str:
        """Get a safe fallback response when content is blocked."""
        return (
            "I'm not able to help with that request. "
            "My safety guidelines prevent me from generating content "
            "that could cause harm. Is there something else I can help you with?"
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
