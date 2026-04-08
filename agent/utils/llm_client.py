from google import genai
from typing import Any, Dict, Optional
import json
import time
from agent.config import settings
from agent.utils.logger import logger

client = genai.Client(api_key=settings.gemini_api_key)


def get_gemini_client():
    return client


def generate_structured_output(
    prompt: str,
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    max_retries: int = 3
) -> Any:
    model = get_gemini_client()
    
    config = {
        "temperature": temperature if temperature is not None else settings.temperature,
        "max_output_tokens": settings.max_output_tokens,
    }
    
    if response_schema:
        config["response_mime_type"] = "application/json"
        config["response_schema"] = response_schema
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            response = model.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=config
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            result = response.text.strip()
            
            logger.info(
                "llm_call_completed",
                latency_ms=latency_ms,
                attempt=attempt + 1,
                response_length=len(result)
            )
            
            if response_schema:
                return json.loads(result)
            return result
            
        except Exception as e:
            logger.warning(
                "llm_call_failed",
                attempt=attempt + 1,
                error=str(e),
                max_retries=max_retries
            )
            
            if attempt == max_retries - 1:
                raise
            
            time.sleep(2 ** attempt)
    
    raise Exception("Max retries exceeded for LLM call")
