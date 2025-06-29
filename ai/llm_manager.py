from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, Future
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

PERPLEXITY_MODELS = {
    "sonar",
    "sonar-pro",
}


_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _get_llm_config():
    settings = get_settings()
    return (
        settings.get("openai_api_key"),
        settings.get("groq_api_key"),
        settings.get("perplexity_api_key"),
        settings.get("llm_model"),
        settings.get("prompts", {}),
    )


def is_configured() -> bool:
    oa_key, groq_key, pplx_key, model, _ = _get_llm_config()
    if model in GROQ_MODELS:
        return bool(groq_key and model)
    if model in PERPLEXITY_MODELS:
        return bool(pplx_key and model)
    return bool(oa_key and model)


def get_prompt(name: str) -> str:
    _oa, _groq, _pplx, _model, prompts = _get_llm_config()
    if name == "company_alias":
        return prompts.get(name, COMPANY_ALIAS_PROMPT)
    return prompts.get(name, "")


def _sanitize_yes_no(text: str) -> str:
    t = text.strip().rstrip(".").strip()
    lower = t.lower()
    if lower.startswith("yes"):
        return "Yes"
    if lower.startswith("no"):
        return "No"
    return t


def _run_prompt_once(
    prompt_name: str,
    variables: dict | None = None,
    clean: bool = True,
    web_search: bool = False,
) -> str:
    oa_key, groq_key, pplx_key, model, prompts = _get_llm_config()
    if model in GROQ_MODELS:
        api_key = groq_key
        if not api_key or Groq is None:
            raise RuntimeError("Groq API key or model not configured")
        client = Groq(api_key=api_key)
        print(f"[Groq] model={model} prompt={prompt_name}")
    elif model in PERPLEXITY_MODELS:
        api_key = pplx_key
        if not api_key:
            raise RuntimeError("Perplexity API key or model not configured")
        client = None
        print(f"[Perplexity] model={model} prompt={prompt_name}")
    else:
        api_key = oa_key
        if not api_key:
            raise RuntimeError("OpenAI API key or model not configured")
        client = OpenAI(api_key=api_key)
        print(f"[OpenAI] model={model} prompt={prompt_name}")
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

    if model in PERPLEXITY_MODELS:
        import requests  # local import to avoid mandatory dependency

        print("[LLM] sending Perplexity request")
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if web_search:
            payload["search_mode"] = "web"
            payload["web_search_options"] = {"search_context_size": "low"}
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    else:
        if web_search:
            if model not in OPENAI_MODELS:
                raise RuntimeError(
                    "Web search is only supported for OpenAI models"
                )
            print("[LLM] performing web search request")
            response = client.responses.create(
                model=model,
                tools=[{"type": "web_search_preview"}],
                input=prompt,
            )
            text = response.output_text
        else:
            print("[LLM] sending chat completion request")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content
    print("[LLM] response received")
    result = text.strip() if clean else text
    if prompt_name in {"target_company_validation", "icp_validation"}:
        result = _sanitize_yes_no(result)
    return result


def run_prompt(
    prompt_name: str,
    variables: dict | None = None,
    clean: bool = True,
    web_search: bool = False,
    double_check: bool = False,
) -> str:
    if (
        double_check
        and prompt_name in {"target_company_validation", "icp_validation"}
    ):
        first = _run_prompt_once(prompt_name, variables, clean, web_search)
        second = _run_prompt_once(prompt_name, variables, clean, web_search)
        if first == second:
            return first
        third = _run_prompt_once(prompt_name, variables, clean, web_search)
        yes_count = [first, second, third].count("Yes")
        return "Yes" if yes_count >= 2 else "No"
    return _run_prompt_once(prompt_name, variables, clean, web_search)


def run_prompt_async(
    prompt_name: str,
    variables: dict | None = None,
    clean: bool = True,
    web_search: bool = False,
    double_check: bool = False,
) -> Future:
    """Run ``run_prompt`` in a background thread and return a ``Future``."""
    return _EXECUTOR.submit(
        run_prompt, prompt_name, variables, clean, web_search, double_check
    )


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
    oa_key, groq_key, pplx_key, model, _ = _get_llm_config()
    if model in GROQ_MODELS:
        api_key = groq_key
        if not api_key or Groq is None:
            raise RuntimeError("Groq API key or model not configured")
        client = Groq(api_key=api_key)
        print(f"[Groq] lookup timezone model={model}")
    elif model in PERPLEXITY_MODELS:
        api_key = pplx_key
        if not api_key:
            raise RuntimeError("Perplexity API key or model not configured")
        client = None
        print(f"[Perplexity] lookup timezone model={model}")
    else:
        api_key = oa_key
        if not api_key:
            raise RuntimeError("OpenAI API key or model not configured")
        client = OpenAI(api_key=api_key)
        print(f"[OpenAI] lookup timezone model={model}")

    date = date or datetime.utcnow().strftime("%Y-%m-%d")

    prompt = (
        "Given the following information, provide ONLY the UTC offset as an "
        "integer (e.g. -4, 0, +2, etc.). If the location is not available or "
        "incomplete, respond with NA. Do not add any explanation or extra text.\n"
        f"Country: {country}\nState: {state}\nCity: {city}\nDate: {date}\nUTC offset:"
    )
    print("[LLM] sending time zone request")
    if model in PERPLEXITY_MODELS:
        import requests

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
    print("[LLM] time zone response received")
    return text.strip()


def lookup_utc_offset_async(
    country: str, state: str, city: str, date: str | None = None
) -> Future:
    """Run ``lookup_utc_offset`` in a background thread and return a ``Future``."""
    return _EXECUTOR.submit(lookup_utc_offset, country, state, city, date)
