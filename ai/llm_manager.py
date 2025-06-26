from datetime import datetime
from openai import OpenAI
from config.settings import get_settings


COMPANY_ALIAS_PROMPT = (
    "Here is the official company name:\n"
    "{company_name}\n"
    "Your task is to return ONLY the short, conversational, or common alias people use to refer to this company.\n"
    "If the name is \u201cThe Walt Disney Company\u201d, return \u201cDisney\u201d.\n"
    "If the name is \u201cA.A. Monkey LLC\u201d, return \u201cA.A. Monkey\u201d.\n"
    "If the name is \u201cPinocho Company by T-Mobile\u201d, return \u201cPinocho\u201d.\n"
    "If there is no obvious alias, just return the most natural main part of the name.\n"
    "Output ONLY the alias, with no extra text, formatting, or explanation."
)


def _get_openai_config():
    settings = get_settings()
    return settings.get("openai_api_key"), settings.get("llm_model"), settings.get("prompts", {})


def is_configured() -> bool:
    api_key, model, _ = _get_openai_config()
    return bool(api_key and model)


def get_prompt(name: str) -> str:
    if name == "company_alias":
        return COMPANY_ALIAS_PROMPT
    _api, _model, prompts = _get_openai_config()
    return prompts.get(name, "")


def run_prompt(prompt_name: str, variables: dict | None = None, clean: bool = True) -> str:
    api_key, model, prompts = _get_openai_config()
    if not api_key or not model:
        raise RuntimeError("OpenAI API key or model not configured")
    if prompt_name == "company_alias":
        template = COMPANY_ALIAS_PROMPT
    else:
        template = prompts.get(prompt_name)
        if not template:
            raise RuntimeError(f"Prompt template '{prompt_name}' not configured")
    variables = variables or {}

    # Format the user's template with the given variables
    prompt = template.format(**variables)

    # Build contextual lines with available variables
    context_lines = []
    key_map = {
        "company_name": "Company Name",
        "headcount": "Headcount",
        "company_description": "Company Description",
        "first_name": "First Name",
        "last_name": "Last Name",
        "job_title": "Job Title",
    }
    for key, label in key_map.items():
        value = variables.get(key)
        if value:
            context_lines.append(f"{label}: {value}")

    for key, value in variables.items():
        if key not in key_map and value not in (None, ""):
            pretty = key.replace("_", " ").title()
            context_lines.append(f"{pretty}: {value}")

    if context_lines:
        prompt = f"{prompt}\n\n" + "\n".join(context_lines)

    if prompt_name in {"target_company_validation", "icp_validation"}:
        prompt += '\n\nAnswer ONLY "Yes" or "No". Do not add anything else.'
    else:
        prompt += (
            "\n\nAnswer ONLY with the specific information requested, without any "
            "explanation or extra formatting."
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content
    return text.strip() if clean else text


def lookup_utc_offset(
    country: str, state: str, city: str, date: str | None = None
) -> str:
    """Return UTC offset for the given location using a dedicated prompt.

    Parameters
    ----------
    country, state, city : str
        Location information used for the lookup.
    date : str, optional
        Date in ``YYYY-MM-DD`` format. If omitted, today's UTC date is used.
    """
    api_key, model, _ = _get_openai_config()
    if not api_key or not model:
        raise RuntimeError("OpenAI API key or model not configured")

    date = date or datetime.utcnow().strftime("%Y-%m-%d")

    prompt = (
        "Given the following information, provide ONLY the UTC offset as an "
        "integer (e.g. -4, 0, +2, etc.). If the location is not available or "
        "incomplete, respond with NA. Do not add any explanation or extra text.\n"
        f"Country: {country}\nState: {state}\nCity: {city}\nDate: {date}\nUTC offset:"
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()
