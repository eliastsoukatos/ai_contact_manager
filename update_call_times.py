import argparse
from db_manager import DBManager
from ai.enrichment import _calculate_call_times, lookup_utc_offset


def update_call_times(force_lookup: bool = False) -> int:
    """Recalculate call times for all contacts.

    Parameters
    ----------
    force_lookup : bool, optional
        If True, lookup the UTC offset for contacts missing the ``time_zone_utc``
        field using the OpenAI API. Otherwise only contacts with an existing
        ``time_zone_utc`` value will be processed.

    Returns
    -------
    int
        Number of contacts updated.
    """
    db = DBManager()
    contacts = db.fetch_contacts()
    count = 0

    for c in contacts:
        tz = c.get("time_zone_utc")
        if (not tz or tz == "NA") and force_lookup:
            try:
                tz = lookup_utc_offset(
                    c.get("country", ""),
                    c.get("state", ""),
                    c.get("city", ""),
                )
            except Exception:
                tz = None
        if not tz or tz == "NA":
            morning, afternoon = "NA", "NA"
        else:
            morning, afternoon = _calculate_call_times(tz)
        if (
            c.get("morning_call_time") != morning
            or c.get("afternoon_call_time") != afternoon
            or (force_lookup and tz != c.get("time_zone_utc"))
        ):
            update = {
                "morning_call_time": morning,
                "afternoon_call_time": afternoon,
            }
            if force_lookup and tz and tz != c.get("time_zone_utc"):
                update["time_zone_utc"] = tz
            db.update_contact(c["profile_id"], update)
            count += 1
    db.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Recalculate call times")
    parser.add_argument(
        "--force-lookup",
        action="store_true",
        help="lookup missing UTC offsets using OpenAI",
    )
    args = parser.parse_args()
    updated = update_call_times(force_lookup=args.force_lookup)
    print(f"Updated {updated} contacts")


if __name__ == "__main__":
    main()
