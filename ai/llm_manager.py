from datetime import datetime
import re
from openai import OpenAI
try:
    from groq import Groq
except Exception:  # pragma: no cover - optional dependency
    Groq = None
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


OPENAI_MODELS = {
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini",
    "o3-mini",
}

GROQ_MODELS = {
    "gemma2-9b-it",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-guard-4-12b",
}


def _get_llm_config():
    settings = get_settings()
    return (
        settings.get("openai_api_key"),
        settings.get("groq_api_key"),
        settings.get("llm_model"),
        settings.get("prompts", {}),
    )


def is_configured() -> bool:
    oa_key, groq_key, model, _ = _get_llm_config()
    if model in GROQ_MODELS:
        return bool(groq_key and model)
    return bool(oa_key and model)


def get_prompt(name: str) -> str:
    _oa, _groq, _model, prompts = _get_llm_config()
    if name == "company_alias":
        return prompts.get(name, COMPANY_ALIAS_PROMPT)
    return prompts.get(name, "")


def run_prompt(
    prompt_name: str,
    variables: dict | None = None,
    clean: bool = True,
    web_search: bool = False,
) -> str:
    oa_key, groq_key, model, prompts = _get_llm_config()
    if model in GROQ_MODELS:
        api_key = groq_key
        if not api_key or Groq is None:
            raise RuntimeError("Groq API key or model not configured")
        client = Groq(api_key=api_key)
    else:
        api_key = oa_key
        if not api_key:
            raise RuntimeError("OpenAI API key or model not configured")
        client = OpenAI(api_key=api_key)
    if prompt_name == "company_alias":
        template = prompts.get(prompt_name, COMPANY_ALIAS_PROMPT)
    else:
        template = prompts.get(prompt_name)
        if not template:
            raise RuntimeError(f"Prompt template '{prompt_name}' not configured")
    variables = variables or {}

    # Replace {{var}} placeholders with the corresponding values
    def _replace(match: re.Match) -> str:
        return str(variables.get(match.group(1), ""))

    prompt = re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, template)

    if prompt_name in {"target_company_validation", "icp_validation"}:
        prompt += '\n\nAnswer ONLY "Yes" or "No". Do not add anything else.'
    else:
        prompt += (
            "\n\nAnswer ONLY with the specific information requested, without any "
            "explanation or extra formatting."
        )

    if web_search:
        if model not in OPENAI_MODELS:
            raise RuntimeError("Web search is only supported for OpenAI models")
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        text = response.output_text
    else:
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
    oa_key, groq_key, model, _ = _get_llm_config()
    if model in GROQ_MODELS:
        api_key = groq_key
        if not api_key or Groq is None:
            raise RuntimeError("Groq API key or model not configured")
        client = Groq(api_key=api_key)
    else:
        api_key = oa_key
        if not api_key:
            raise RuntimeError("OpenAI API key or model not configured")
        client = OpenAI(api_key=api_key)

    date = date or datetime.utcnow().strftime("%Y-%m-%d")

    prompt = (
        "Given the following information, provide ONLY the UTC offset as an "
        "integer (e.g. -4, 0, +2, etc.). If the location is not available or "
        "incomplete, respond with NA. Do not add any explanation or extra text.\n"
        f"Country: {country}\nState: {state}\nCity: {city}\nDate: {date}\nUTC offset:"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()
