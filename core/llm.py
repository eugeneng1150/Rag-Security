import os
import time
import logging
from langchain_openai import ChatOpenAI
from core.config import load_config

logger = logging.getLogger(__name__)

MAX_RETRIES = 10
RETRY_DELAY = 2


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
        max_retries=overrides.pop("max_retries", 0),
        request_timeout=overrides.pop("request_timeout", 120),
        **overrides,
    )


def invoke_with_retry(llm, messages, max_retries=MAX_RETRIES):
    """Invoke LLM with fixed-interval retry for content filter and transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return llm.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            is_retryable = (
                "429" in err_str
                or "rate limit" in err_str
                or "too many requests" in err_str
                or "server error" in err_str
                or "500" in err_str
                or "502" in err_str
                or "503" in err_str
                or "504" in err_str
                or "timeout" in err_str
                or "content filter" in err_str
                or "content_filter" in err_str
                or "responsibleaipolicy" in err_str
            )
            if is_retryable and attempt < max_retries:
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s — retrying in %ds",
                    attempt + 1, max_retries + 1, str(e)[:200], RETRY_DELAY,
                )
                time.sleep(RETRY_DELAY)
            else:
                raise
