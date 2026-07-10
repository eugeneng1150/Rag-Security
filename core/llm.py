from langchain_openai import ChatOpenAI
from core.config import load_config


def get_llm(config=None, **overrides):
    if config is None:
        config = load_config()

    return ChatOpenAI(
        base_url=config.model.base_url,
        api_key=config.model.api_key,
        model=config.model.model_name,
        temperature=overrides.pop("temperature", config.model.temperature),
        max_tokens=overrides.pop("max_tokens", config.model.max_tokens),
        **overrides,
    )
