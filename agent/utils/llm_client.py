from typing import Any, Dict, Optional
import json
import time
import httpx
from google import genai
from agent.config import settings
from agent.utils.logger import logger

_gemini_client = genai.Client(api_key=settings.gemini_api_key)


def get_gemini_client():
    return _gemini_client


def _get_provider() -> str:
    return (settings.llm_provider or "gemini").strip().lower()


def _resolve_model_name(provider: str) -> str:
    model_name = settings.model_name
    if provider == "openai" and model_name.startswith("gemini"):
        return "gpt-4o-mini"
    return model_name


def _generate_with_openai(
    prompt: str,
    response_schema: Optional[Dict[str, Any]],
    temperature: float,
) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    user_prompt = prompt
    if response_schema:
        user_prompt = (
            "Return ONLY valid JSON that follows the expected structure.\n\n"
            f"{prompt}"
        )

    payload: Dict[str, Any] = {
        "model": _resolve_model_name("openai"),
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
        "max_tokens": settings.max_output_tokens,
    }

    if response_schema:
        payload["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def _generate_with_gemini(
    prompt: str,
    response_schema: Optional[Dict[str, Any]],
    temperature: float,
) -> str:
    model = get_gemini_client()
    config: Dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": settings.max_output_tokens,
    }

    if response_schema:
        config["response_mime_type"] = "application/json"
        config["response_schema"] = response_schema

    response = model.models.generate_content(
        model=_resolve_model_name("gemini"),
        contents=prompt,
        config=config,
    )
    return response.text.strip()


def generate_structured_output(
    prompt: str,
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    max_retries: int = 3
) -> Any:
    provider = _get_provider()
    chosen_temperature = temperature if temperature is not None else settings.temperature

    for attempt in range(max_retries):
        try:
            start_time = time.time()

            if provider == "openai":
                result = _generate_with_openai(
                    prompt=prompt,
                    response_schema=response_schema,
                    temperature=chosen_temperature,
                )
            else:
                result = _generate_with_gemini(
                    prompt=prompt,
                    response_schema=response_schema,
                    temperature=chosen_temperature,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "llm_call_completed",
                latency_ms=latency_ms,
                attempt=attempt + 1,
                response_length=len(result),
                provider=provider,
            )

            if response_schema:
                return json.loads(result)
            return result

        except Exception as e:
            logger.warning(
                "llm_call_failed",
                attempt=attempt + 1,
                error=str(e),
                max_retries=max_retries,
                provider=provider,
            )

            if attempt == max_retries - 1:
                raise

            time.sleep(2 ** attempt)

    raise Exception("Max retries exceeded for LLM call")
