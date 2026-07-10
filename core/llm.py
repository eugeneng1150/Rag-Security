import os
from langchain_openai import ChatOpenAI
from core.config import load_config


def get_llm(config=None, **overrides):
    if config is None:
        config = load_config()

    api_key = config.model.api_key
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, "")
        if not api_key:
            raise RuntimeError(f"Environment variable {env_var} is not set. Export it first.")

    return ChatOpenAI(
        base_url=config.model.base_url,
        api_key=api_key,
        model=config.model.model_name,
        temperature=overrides.pop("temperature", config.model.temperature),
        max_tokens=overrides.pop("max_tokens", config.model.max_tokens),
        **overrides,
    )
