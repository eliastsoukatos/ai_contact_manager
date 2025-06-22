from typing import Callable, Dict, List
from db_manager import DBManager
from .llm_manager import run_prompt, is_configured


AI_FIELDS = [
    "clients_of_contact",
    "area_of_business",
    "most_relevant_summit",
    "client_icp",
    "time_zone_utc",
]


def estimate_steps(db: DBManager) -> int:
    contacts = db.fetch_contacts()
    companies = {
        (c.get("website") or c.get("company_name"))
        for c in contacts
        if not c.get("target_company")
    }
    total = len(companies)
    for c in contacts:
        if (c.get("target_company") or "").lower().startswith("y"):
            if not c.get("contact_icp_status"):
                total += 1
            if (c.get("contact_icp_status") or "").lower().startswith("y"):
                for field in AI_FIELDS:
                    if not c.get(field):
                        total += 1
    return total


def enrich_database(
    db: DBManager,
    progress_callback: Callable[[int, int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> None:
    if not is_configured():
        raise RuntimeError("OpenAI API key or model not configured")
    progress_callback = progress_callback or (lambda c, t: None)
    status_callback = status_callback or (lambda m: None)

    contacts = db.fetch_contacts()
    total = estimate_steps(db)
    step = 0

    # Company enrichment
    companies: Dict[str, List[dict]] = {}
    for c in contacts:
        key = c.get("website") or c.get("company_name")
        if not key:
            continue
        companies.setdefault(key, []).append(c)

    for key, clist in companies.items():
        missing = [c for c in clist if not c.get("target_company")]
        if not missing:
            continue
        sample = missing[0]
        try:
            result = run_prompt(
                "target_company_validation",
                {
                    "company_name": sample.get("company_name", ""),
                    "company_description": sample.get("company_description", ""),
                    "headcount": sample.get("headcount", ""),
                    "website": sample.get("website", ""),
                },
            )
            for c in missing:
                db.update_contact(c["profile_id"], {"target_company": result})
        except Exception as exc:  # noqa: BLE001
            status_callback(str(exc))
        step += 1
        progress_callback(step, total)

    contacts = db.fetch_contacts()
    for c in contacts:
        if (c.get("target_company") or "").lower().startswith("y"):
            if not c.get("contact_icp_status"):
                try:
                    result = run_prompt("icp_validation", c)
                    db.update_contact(c["profile_id"], {"contact_icp_status": result})
                except Exception as exc:  # noqa: BLE001
                    status_callback(str(exc))
                step += 1
                progress_callback(step, total)
            if (c.get("contact_icp_status") or "").lower().startswith("y"):
                for field, prompt in {
                    "clients_of_contact": "clients_of_contact",
                    "area_of_business": "area_of_business",
                    "most_relevant_summit": "most_relevant_summit",
                    "client_icp": "client_icp",
                }.items():
                    if not c.get(field):
                        try:
                            result = run_prompt(prompt, c)
                            db.update_contact(c["profile_id"], {field: result})
                        except Exception as exc:  # noqa: BLE001
                            status_callback(str(exc))
                        step += 1
                        progress_callback(step, total)
                if not c.get("time_zone_utc"):
                    try:
                        result = run_prompt("time_zone_lookup", c)
                        db.update_contact(c["profile_id"], {"time_zone_utc": result})
                    except Exception as exc:  # noqa: BLE001
                        status_callback(str(exc))
                    step += 1
                    progress_callback(step, total)
