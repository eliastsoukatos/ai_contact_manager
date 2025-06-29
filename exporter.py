import os
import re
from typing import List, Tuple, Dict, Optional

from ai.enrichment import _calculate_call_times


def _snake_case(text: str) -> str:
    cleaned = text.strip().lower()
    return re.sub(r"[\s/-]+", "_", cleaned)


def _chunk_list(items: List[dict], groups: int, chunk_size: Optional[int] = None) -> List[List[dict]]:
    """Split *items* into *groups* or by *chunk_size*."""
    if chunk_size:
        if chunk_size <= 0:
            groups = 1
        chunks = []
        for i in range(0, len(items), chunk_size if chunk_size > 0 else len(items)):
            chunks.append(items[i : i + chunk_size])
        return chunks

    groups = max(1, groups)
    k, m = divmod(len(items), groups)
    chunks = []
    start = 0
    for i in range(groups):
        end = start + k + (1 if i < m else 0)
        chunks.append(items[start:end])
        start = end
    return chunks


def _format_csv_value(value: str) -> str:
    """Return a CSV-safe version of *value* with quoting when needed."""
    if value is None:
        value = ""
    text = str(value)
    if any(ch in text for ch in ["\n", "\r", "\t", ",", '"']):
        text = text.replace('"', '""')
        return f'"{text}"'
    return text


def export_contacts(
    contacts: List[dict],
    headers: List[str],
    export_dir: str,
    groups: int = 1,
    split_by_tz: bool = False,
    chunk_size: Optional[int] = None,
) -> int:
    """Export contacts to CSV files.

    Parameters
    ----------
    contacts : list of dict
        Contacts to export.
    headers : list of str
        Visible headers in the current table.
    export_dir : str
        Target directory where CSV files will be written.
    groups : int, optional
        How many groups/chunks each time zone should be split into when
        ``chunk_size`` is not specified.
    split_by_tz : bool, optional
        Whether to create separate files for each time zone.
    chunk_size : int, optional
        Maximum number of contacts per file. Overrides ``groups`` when set.

    Returns
    -------
    int
        Number of CSV files created.
    """
    os.makedirs(export_dir, exist_ok=True)

    header_row = ["phone_number"] + [
        _snake_case(h) for h in headers if h != "mobile"
    ]

    file_count = 0

    if split_by_tz:
        tz_groups: Dict[Optional[str], List[dict]] = {}
        for c in contacts:
            tz = c.get("time_zone_utc")
            tz_groups.setdefault(tz, []).append(c)
    else:
        tz_groups = {None: contacts}

    for tz, clist in tz_groups.items():
        if not clist:
            continue
        tz_suffix = ""
        morning, afternoon = "NA", "NA"
        if split_by_tz:
            morning, afternoon = _calculate_call_times(tz)
            tz_suffix = f"{morning.replace(':', '_')}-{afternoon.replace(':', '_')}"

        chunks = _chunk_list(clist, groups, chunk_size)
        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue
            group_name = f"Group_{chr(ord('A') + idx)}"
            parts = [group_name]
            if split_by_tz:
                parts.append(tz_suffix)
            filename = "_".join(parts) + ".csv"
            path = os.path.join(export_dir, filename)
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(",".join(_format_csv_value(h) for h in header_row) + "\r\n")
                for contact in chunk:
                    row = [contact.get("mobile", "")]
                    row += [contact.get(h, "") for h in headers if h != "mobile"]
                    f.write(",".join(_format_csv_value(v) for v in row) + "\r\n")
            file_count += 1

    return file_count
