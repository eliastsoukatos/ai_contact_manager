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


def disposition_to_status(disposition: str) -> str:
    """Return the status string for a given contact disposition."""
    if not disposition:
        disposition = "not_defined"
    return "inactive" if disposition in INACTIVE_DISPOSITIONS else "active"

