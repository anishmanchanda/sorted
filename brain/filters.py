"""Cheap local filters that run before anything is stored or sent to an LLM."""

import re

_OTP = re.compile(
    r"\b(?:otp|one[\s-]?time[\s-]?password|verification code|security code)\b\W+(?:\S+\s+){0,10}?\d{4,8}\b"
    r"|\b\d{4,8}\b\W+(?:\S+\s+){0,3}?(?:otp|verification code)\b",
    re.I,
)
_INJECTION = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) instructions"
    r"|disregard (?:all |any )?(?:previous|prior|the above)"
    r"|you are now (?:in )?\w+ mode"
    r"|system prompt"
    r"|forward (?:all|every|this) (?:mail|email|message)",
    re.I,
)


def is_otp(text: str) -> bool:
    return bool(_OTP.search(text))


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))
