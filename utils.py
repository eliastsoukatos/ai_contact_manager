"""Miscellaneous constants and helpers."""

INACTIVE_DISPOSITIONS = {
    "not_defined",
    "wrong_number",
    "not_in_service",
    "do_not_call",
    "referred_to_another_contact",
    "unreachable",
    "wrong_company",
    "connected_negative",
    "connected_meeting_booked",
    "connected_positive",
}

# Soft highlight colors used for dispositions and status values. The colors are
# semi-transparent so that text remains readable and the UI isn't overpowered.
DISPOSITION_COLORS = {
    "connected_positive": "rgba(144, 238, 144, 0.4)",  # light green
    "connected_meeting_booked": "rgba(144, 238, 144, 0.4)",
    "connected_neutral": "rgba(255, 255, 128, 0.4)",  # light yellow
    "number_validated": "rgba(255, 255, 128, 0.4)",
    "left_voicemail": "rgba(255, 255, 128, 0.4)",
    "referred_to_another_contact": "rgba(255, 255, 128, 0.4)",
    "busy_call_back_later": "rgba(255, 255, 128, 0.4)",
    "connected_negative": "rgba(255, 182, 193, 0.4)",  # light red
    "wrong_number": "rgba(255, 182, 193, 0.4)",
    "not_in_service": "rgba(255, 182, 193, 0.4)",
    "do_not_call": "rgba(255, 182, 193, 0.4)",
    "unreachable": "rgba(255, 182, 193, 0.4)",
    "wrong_company": "rgba(255, 182, 193, 0.4)",
}

# Status column highlight colors
STATUS_COLORS = {
    "active": "rgba(144, 238, 144, 0.4)",
    "inactive": "rgba(255, 182, 193, 0.4)",
}


def clean_phone_number(number: str) -> str:
    """Return a phone number stripped of extra whitespace and symbols."""
    import re

    cleaned = re.sub(r"[^\d+]+", "", number or "")
    if cleaned.startswith("+"):
        return "+" + cleaned[1:].replace("+", "")
    return cleaned.replace("+", "")


def disposition_to_status(disposition: str) -> str:
    """Return the status string for a given contact disposition."""
    if not disposition:
        disposition = "not_defined"
    return "inactive" if disposition in INACTIVE_DISPOSITIONS else "active"


def disposition_to_color(disposition: str) -> str:
    """Return the highlight color for a given disposition."""
    return DISPOSITION_COLORS.get(disposition, "")


def status_to_color(status: str) -> str:
    """Return the highlight color for a status value."""
    return STATUS_COLORS.get(status, "")

