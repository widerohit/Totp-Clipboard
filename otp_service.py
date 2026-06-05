"""TOTP generation helpers for TOTP Clipboard."""

from __future__ import annotations

import time

import pyotp


OTP_INTERVAL_SECONDS = 30
OTP_DIGITS = 6


class OtpError(ValueError):
    """Raised when an OTP cannot be generated from the supplied profile."""


def normalize_secret(secret: str) -> str:
    """Return a Base32 secret in a form accepted by pyotp."""
    return "".join(secret.upper().split())


def validate_secret(secret: str) -> None:
    """Validate that a secret can produce an RFC6238 TOTP."""
    normalized = normalize_secret(secret)
    if not normalized:
        raise OtpError("Secret is required.")

    try:
        pyotp.TOTP(normalized, digits=OTP_DIGITS, interval=OTP_INTERVAL_SECONDS).now()
    except Exception as exc:
        raise OtpError("Secret must be a valid Base32 TOTP secret.") from exc


def seconds_remaining(now: float | None = None) -> int:
    """Return seconds left in the current 30-second TOTP window."""
    current_time = time.time() if now is None else now
    remaining = OTP_INTERVAL_SECONDS - (int(current_time) % OTP_INTERVAL_SECONDS)
    return OTP_INTERVAL_SECONDS if remaining == 0 else remaining


def generate_totp(secret: str) -> str:
    """Generate a 6-digit RFC6238 TOTP for a Base32 secret."""
    normalized = normalize_secret(secret)
    if not normalized:
        raise OtpError("Secret is required.")
    return pyotp.TOTP(
        normalized,
        digits=OTP_DIGITS,
        interval=OTP_INTERVAL_SECONDS,
    ).now()


def generate_value(base_text: str, secret: str) -> str:
    """Generate the enterprise password value: <BaseText><CurrentTOTP>."""
    return f"{base_text}{generate_totp(secret)}"
