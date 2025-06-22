from openai import OpenAI
from config.settings import get_settings


def _get_openai_config():
    settings = get_settings()
    return settings.get("openai_api_key"), settings.get("llm_model"), settings.get("prompts", {})


def is_configured() -> bool:
    api_key, model, _ = _get_openai_config()
    return bool(api_key and model)


def get_prompt(name: str) -> str:
    _api, _model, prompts = _get_openai_config()
    return prompts.get(name, "")


def run_prompt(prompt_name: str, variables: dict | None = None, clean: bool = True) -> str:
    api_key, model, prompts = _get_openai_config()
    if not api_key or not model:
        raise RuntimeError("OpenAI API key or model not configured")
    template = prompts.get(prompt_name)
    if not template:
        raise RuntimeError(f"Prompt template '{prompt_name}' not configured")
    variables = variables or {}
    prompt = template.format(**variables)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content
    return text.strip() if clean else text
