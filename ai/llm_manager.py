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
